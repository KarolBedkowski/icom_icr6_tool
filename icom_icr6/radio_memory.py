# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

from __future__ import annotations

import itertools
import logging
import typing as ty
from collections import defaultdict

from . import consts, fixers, model

_LOG = logging.getLogger(__name__)
DEBUG = True


def region_from_etcdata(etcdata: str) -> consts.Region:
    """Looks like etcdata contain 5 bits of "region",
    there are also some unknown flags at last two bit. Rest is some
    checksum - seems to checksum is arithmetic sum of all "1" in region and
    flags & 7. Bits: (r=market, C=checksum, f=some flag)
        fedcba98 76543210
        ------rr rCrrCffC
    """
    etc = int(etcdata, 16)
    area = ((etc & 0b1110000000) >> 5) | ((etc & 0b110000) >> 4)
    match area:
        case 0 | 14 | 15:
            return consts.Region.JAPAN
        case 2:
            return consts.Region.GLOBAL2
        case 6:
            return consts.Region.USA
        case 13:
            return consts.Region.FRANCE  # ??

    return consts.Region.GLOBAL


def etcdata_from_region(region: consts.Region) -> str:
    """Map region to etcdata; this may be inaccurate as i.e. Japan uses
    probably more that one etcdata code; also there are also unknown flags.
    """
    match region:
        case consts.Region.GLOBAL2:
            return "002A"
        case consts.Region.JAPAN:
            return "0003"
        case consts.Region.USA:
            return "00AB"
        case consts.Region.FRANCE:
            return "01D2"

    return "001A"


class RadioMemory:
    def __init__(self) -> None:
        self.mem = bytearray(consts.MEM_SIZE)

        self.file_comment = ""
        self.file_maprev = "1"
        self.file_etcdata = ""
        self.region = consts.Region.GLOBAL

        self.channels: list[model.Channel] = []
        self.banks: list[model.Bank] = []
        self.scan_links: list[model.ScanLink] = []
        self.scan_edges: list[model.ScanEdge] = []
        self.settings: model.RadioSettings
        # read-only
        self.awchannels: list[model.Channel] = []
        self.bank_links: model.BankLinks
        self.comment = ""
        self.bands: list[model.BandDefaults] = []

    def update_from(self, rm: RadioMemory) -> None:
        """Load memory data from other RadioMemory."""
        self.mem = rm.mem
        self.file_comment = rm.file_comment
        self.file_maprev = rm.file_maprev
        self.file_etcdata = rm.file_etcdata
        self.load_memory()

    def update_mem_region(self, addr: int, data: bytes) -> None:
        """Update map region from `addr` with `data`."""
        self.mem[addr : addr + len(data)] = data

    def validate(self) -> None:
        """Validate memory. Do not validate loaded objects."""
        if (memlen := len(self.mem)) != consts.MEM_SIZE:
            err = f"invalid memory size: {memlen}"
            raise ValueError(err)

        mem_footer = bytes(
            self.mem[consts.MEM_SIZE - len(consts.MEM_FOOTER) :]
        ).decode()
        if mem_footer != consts.MEM_FOOTER:
            err = f"invalid memory footer: {mem_footer}"
            raise ValueError(err)

        _LOG.debug("region: %r", self.file_etcdata)

    def load_memory(self) -> None:
        self._load_channels()
        self._load_autowrite_channels()
        self._load_banks()
        self._load_bank_links()
        self._load_scan_edge()
        self._load_scan_links()
        self._load_settings()
        self._load_comment()
        self._load_bands()

        if self.file_etcdata:
            self.region = region_from_etcdata(self.file_etcdata)
            _LOG.debug("region: %r", self.region)
        else:
            self.region = self._guess_region()
            _LOG.debug("region: %r (guess)", self.region)
            self.file_etcdata = etcdata_from_region(self.region)

    def commit(self) -> None:
        """Write data to mem."""
        _LOG.debug("commit")
        self._save_channels()
        self._save_scan_edges()
        self._save_scan_links()
        self._save_banks()
        self._save_bank_links()
        self._save_settings()
        self._save_comment()

    def find_first_hidden_channel(
        self, start: int = 0
    ) -> model.Channel | None:
        """Find first hidden channel starting from `start` position."""
        for chan in self.channels[start:]:
            if chan.hide_channel:
                return chan

        return None

    def get_active_channels(self) -> ty.Iterable[model.Channel]:
        for chan in self.channels:
            if not chan.hide_channel:
                yield chan

    def get_bank_channels(self, bank_idx: int) -> model.BankChannels:
        """this return only first channel on bank position."""
        _LOG.debug("get_bank_channels %d", bank_idx)
        if bank_idx < 0 or bank_idx > consts.NUM_BANKS - 1:
            raise IndexError

        bc = model.BankChannels()
        bc.set(self.get_channels_in_bank(bank_idx))
        return bc

    def get_channels_in_bank(self, bank: int) -> ty.Iterable[model.Channel]:
        """Get active channels in bank."""
        for chan in self.channels:
            if chan.bank == bank and not chan.hide_channel:
                yield chan

    def get_dupicated_bank_pos(self) -> set[int]:
        """Return list of channels that occupy one position in bank."""
        banks_pos: defaultdict[tuple[int, int], list[int]] = defaultdict(list)

        for channum, chan in enumerate(self.channels):
            if chan.bank != consts.BANK_NOT_SET and not chan.hide_channel:
                banks_pos[(chan.bank, chan.bank_pos)].append(channum)

        return set(
            itertools.chain.from_iterable(
                chans for chans in banks_pos.values() if len(chans) > 1
            )
        )

    def is_bank_pos_duplicated(
        self, bank: int, bank_pos: int, channum: int
    ) -> bool:
        for idx, chan in enumerate(self.channels):
            if (
                channum != idx
                and chan.bank == bank
                and chan.bank_pos == bank_pos
                and not chan.hide_channel
            ):
                return True

        return False

    def is_japan_model(self) -> bool:
        return self.region == consts.Region.JAPAN

    def is_usa_model(self) -> bool:
        return self.region == consts.Region.USA

    def validate_loaded_data(self) -> None:
        # check for doubled banks entries
        if channels := self.get_dupicated_bank_pos():
            errmsg = "Bank with invalid (doubled) bank position: " + ", ".join(
                map(str, channels)
            )
            raise ValueError(errmsg)

    def get_band_for_freq(self, freq: int) -> model.BandDefaults:
        # TODO: don't know how to detect other regions
        # for US and EUR/Global is the same
        # there is only difference in WFM minimal frequency for Japan (guess)
        match self.region:
            case consts.Region.FRANCE:
                bands = consts.BANDS_FRANCE
            case consts.Region.JAPAN:
                bands = consts.BANDS_JAP
            case _:
                bands = consts.BANDS_DEFAULT

        for idx, max_freq in enumerate(bands):
            if freq < max_freq:
                # band configuration is loaded from radio memory (bands)
                band = self.bands[idx]
                _LOG.debug("get_band_for_freq: %d: %r", freq, band)
                return band

        _LOG.error("get_band_for_freq: %d: not found", freq)
        raise ValueError

    def find(self, query: str) -> ty.Iterable[tuple[str, object]]:
        """Find object that match `query` string.

        Return tuple[object type, object]
        """
        for chan in self.channels:
            if chan.hide_channel:
                continue

            if str(chan.freq).startswith(query) or chan.name.startswith(query):
                yield "channel", chan

                if chan.bank != consts.BANK_NOT_SET:
                    yield "bank_pos", chan

        for se in self.awchannels:
            if str(se.freq).startswith(query):
                yield "awchannel", se

    def find_duplicated_channels_freq(
        self,
        precision: int = 1,
        *,
        ignore_mode: bool = False,
        ignore_bank: bool = False,
    ) -> ty.Iterable[tuple[int, int, list[model.Channel]]]:
        """Find active channels with the same frequency (after round last
        `precision` digits).
        yield (rounded frequency, number of channels for this freq,
        channel)
        """
        div = pow(10, precision)

        freq_channels: defaultdict[tuple[int, int, int], list[model.Channel]]
        freq_channels = defaultdict(list)

        for chan in self.channels:
            if not chan.hide_channel:
                key = (
                    chan.freq // div,
                    0 if ignore_mode else chan.mode,
                    0 if ignore_bank else chan.bank,
                )
                freq_channels[key].append(chan)

        for key, channels in freq_channels.items():
            if (num := len(channels)) > 1:
                freq = key[0] * div
                yield freq, num, channels

    # Loading and Writing

    def _load_channels(self) -> None:
        self.channels = channels = []
        mv = memoryview(self.mem)

        for idx in range(consts.NUM_CHANNELS):
            start = idx * 16
            cflags_start = idx * 2 + 0x5F80

            channels.append(
                model.Channel.from_data(
                    idx,
                    mv[start : start + 16],
                    mv[cflags_start : cflags_start + 2],
                )
            )

    def _save_channels(self) -> None:
        mv = memoryview(self.mem)

        for idx, chan in enumerate(self.channels):
            assert idx == chan.number

            if not chan.updated:
                continue

            start = idx * 16
            cflags_start = idx * 2 + 0x5F80

            chan.to_data(
                mv[start : start + 16], mv[cflags_start : cflags_start + 2]
            )
            chan.updated = False

    def _load_autowrite_channels(self) -> None:
        # load position map
        mv = memoryview(self.mem)

        # load hidden flags
        chan_hidden = list(
            bitarray2bits(mv[0x6A10:], consts.NUM_AUTOWRITE_CHANNELS)
        )
        # chan position map
        chan_positiions = mv[0x6A30 : 0x6A30 + consts.NUM_AUTOWRITE_CHANNELS]
        channels = []

        # load only channels that have valid position and are not hidden
        for idx, (hidden, chan_pos) in enumerate(
            zip(chan_hidden, chan_positiions, strict=True)
        ):
            if hidden or chan_pos >= consts.NUM_AUTOWRITE_CHANNELS:
                continue

            start = idx * 16 + 0x5140
            data = mv[start : start + 16]
            channels.append(model.Channel.from_data(chan_pos, data, None))

        # sort channels by position in awchan list
        channels.sort()
        # assign new channel numbers
        for idx, ch in enumerate(channels):
            ch.number = idx

        self.awchannels = channels

    def _load_scan_edge(self) -> None:
        self.scan_edges = ses = []
        mv = memoryview(self.mem)

        for idx in range(consts.NUM_SCAN_EDGES):
            start = 0x5DC0 + idx * 16
            start_flags = 0x69A8 + 4 * idx
            ses.append(
                model.ScanEdge.from_data(
                    idx,
                    mv[start : start + 16],
                    mv[start_flags : start_flags + 3],
                )
            )

    def _save_scan_edges(self) -> None:
        mv = memoryview(self.mem)

        for idx, se in enumerate(self.scan_edges):
            assert idx == se.idx

            if not se.updated:
                continue

            start = 0x5DC0 + se.idx * 16
            start_flags = 0x69A8 + 4 * idx
            se.to_data(
                mv[start : start + 16], mv[start_flags : start_flags + 4]
            )
            se.updated = False

    # not used due to update via channel
    # def _get_channel_flags(self, idx: int) -> ChannelFlags:
    #     if idx < 0 or idx > consts.NUM_CHANNELS - 1:
    #         raise IndexError

    #     cflags_start = idx * 2 + 0x5F80
    #     return ChannelFlags.from_data(
    #         idx,
    #         self.mem[cflags_start : cflags_start + 2],
    #     )

    # def _set_channel_flags(self, cf: ChannelFlags) -> None:
    #     if cf.hide_channel:
    #         cf.bank = consts.BANK_NOT_SET

    #     cflags_start = cf.channum * 2 + 0x5F80
    #     mv = memoryview(self.mem)
    #     mem_flags = mv[cflags_start : cflags_start + 2]
    #     cf.to_data(mem_flags)

    def _load_banks(self) -> None:
        self.banks = banks = []
        mv = memoryview(self.mem)
        for idx in range(consts.NUM_BANKS):
            start = 0x6D10 + idx * 8
            banks.append(model.Bank.from_data(idx, mv[start : start + 8]))

    def _save_banks(self) -> None:
        mv = memoryview(self.mem)
        for idx, bank in enumerate(self.banks):
            assert idx == bank.idx
            start = 0x6D10 + idx * 8
            bank.to_data(mv[start : start + 8])

    def _load_scan_links(self) -> None:
        self.scan_links = sls = []
        mv = memoryview(self.mem)
        for idx in range(consts.NUM_SCAN_LINKS):
            start = 0x6DC0 + idx * 8
            # edges
            estart = 0x6C2C + 4 * idx

            sls.append(
                model.ScanLink.from_data(
                    idx, mv[start : start + 8], mv[estart : estart + 4]
                )
            )

    def _save_scan_links(self) -> None:
        mv = memoryview(self.mem)

        for idx, sl in enumerate(self.scan_links):
            assert idx == sl.idx
            start = 0x6DC0 + idx * 8
            # edges mapping
            estart = 0x6C2C + 4 * idx
            sl.to_data(mv[start : start + 8], mv[estart : estart + 4])

    def _load_settings(self) -> None:
        self.settings = model.RadioSettings.from_data(
            self.mem[0x6BD0 : 0x6BD0 + 64]
        )

    def _save_settings(self) -> None:
        mv = memoryview(self.mem)
        if self.settings.updated:
            self.settings.to_data(mv[0x6BD0 : 0x6BD0 + 64])
            self.settings.updated = False

    def _load_bank_links(self) -> None:
        self.bank_links = model.BankLinks.from_data(
            self.mem[0x6C28 : 0x6C28 + 3]
        )

    def _save_bank_links(self) -> None:
        mv = memoryview(self.mem)
        self.bank_links.to_data(mv[0x6C28 : 0x6C28 + 3])

    def _load_comment(self) -> None:
        self.comment = self.mem[0x6D00 : 0x6D00 + 16].decode().rstrip()

    def _save_comment(self) -> None:
        cmt = fixers.fix_comment(self.comment).ljust(16).encode()
        mv = memoryview(self.mem)
        mv[0x6D00 : 0x6D00 + 16] = cmt

    def _load_bands(self) -> None:
        self.bands = bands = []
        mv = memoryview(self.mem)
        for idx in range(13):
            start = 0x6B00 + idx * 16
            bands.append(
                model.BandDefaults.from_data(idx, mv[start : start + 16])
            )

    def _guess_region(self) -> consts.Region:
        """Guess region from configuration of default bands."""
        if self.bands[0].tuning_step == 14:  # noqa: PLR2004
            return consts.Region.JAPAN

        if self.bands[3].tuning_step == self.bands[10].tuning_step == 7:  # noqa: PLR2004
            return consts.Region.FRANCE

        if self.bands[1].tuning_step == 4:  # noqa: PLR2004
            return consts.Region.USA

        if self.bands[3].tuning_step == 7:  # noqa: PLR2004
            return consts.Region.GLOBAL2

        return consts.Region.GLOBAL


def bitarray2bits(
    data: memoryview | bytes | list[int], number: int
) -> ty.Iterable[bool]:
    for n in range(number):
        pos, bit = divmod(n, 8)
        yield bool(data[pos] & (1 << bit))

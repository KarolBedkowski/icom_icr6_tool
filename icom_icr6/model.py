# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
# ruff: noqa: PLR2004
""" """

from __future__ import annotations

import binascii
import copy
import logging
import typing as ty
from collections import abc
from dataclasses import dataclass, field

from . import coding, consts, fixers, validators

_LOG = logging.getLogger(__name__)
DEBUG = True

MutableMemory = abc.MutableSequence[int] | memoryview


@dataclass
class RadioModel:
    # Data format - 40B
    # model: 4B
    # unknown: 1B - is this mapped to region?
    # rev: 1B
    # comment: 16B
    # unknown: 3B
    # serial 14B
    #    4B
    #    1B unknown
    #    2B
    # unknown 7B
    model: bytes
    rev: int
    comment: str
    serial: str

    debug_info: dict[str, object] | None = None

    @classmethod
    def from_data(
        cls: type[RadioModel], data: bytes | bytearray | memoryview
    ) -> RadioModel:
        serial = binascii.unhexlify(data[25 : 25 + 14])
        serial_decoded = (
            f"{serial[0]<<8|serial[1]:04d}"
            f"{serial[2]:02d}{serial[3]:02d}"
            f"{serial[5]<<8|serial[6]:04d}"
        )

        debug_info = (
            {
                "raw": binascii.hexlify(data),
                "unk1": data[4],
                "unk2": data[22:25],
                "unk_serial": serial[4],
            }
            if DEBUG
            else None
        )

        return RadioModel(
            model=bytes(data[0:4]),
            rev=data[5],
            comment=bytes(data[6:22]).decode(),
            serial=serial_decoded,
            debug_info=debug_info,
        )

    def is_icr6(self) -> bool:
        return self.model == b"\x32\x50\x00\x01"

    def human_model(self) -> str:
        return binascii.hexlify(self.model).decode()


def _is_valid_index(
    inlist: ty.Collection[object], idx: int, name: str
) -> None:
    if idx < 0 or idx >= len(inlist):
        raise ValidateError(name, idx)


def _try_get(inlist: list[str] | tuple[str, ...], idx: int) -> str:
    try:
        return inlist[idx]
    except IndexError:
        return f"<[{idx}]>"


def get_index_or_default(
    inlist: ty.Sequence[str], value: object, default: int = 0
) -> int:
    strval = value if isinstance(value, str) else str(value)
    try:
        return inlist.index(strval)
    except ValueError:
        return default


def obj2bool(val: object) -> bool:
    if isinstance(val, str):
        return val.lower() in ("yes", "y", "true", "t")

    return bool(val)


def bool2bit(val: bool | int, mask: int) -> int:
    return mask if val else 0


def data_set_bit(
    data: MutableMemory,
    offset: int,
    bit: int,
    value: object,
) -> None:
    """Set one `bit` in byte `data[offset]` to `value`."""
    if value:
        data[offset] = data[offset] | (1 << bit)
    else:
        data[offset] = data[offset] & (~(1 << bit))


def data_set(
    data: MutableMemory,
    offset: int,
    mask: int,
    value: int,
) -> None:
    """Set bits indicated by `mask` in byte `data[offset]` to `value`."""
    data[offset] = (data[offset] & (~mask)) | (value & mask)


def bitarray2bits(
    data: memoryview | bytes | list[int], number: int
) -> ty.Iterable[bool]:
    for n in range(number):
        pos, bit = divmod(n, 8)
        yield bool(data[pos] & (1 << bit))


class ValidateError(ValueError):
    def __init__(self, field_name: str, value: object) -> None:
        self.field = field_name
        self.value = value

    def __str__(self) -> str:
        return f"invalid value in {self.field}: {self.value!r}"


@dataclass
class ChannelFlags:
    channum: int
    # control flags
    hide_channel: bool
    skip: int
    # 31 = no bank
    bank: int
    bank_pos: int

    debug_info: dict[str, object] | None = None

    @classmethod
    def from_data(
        cls: type[ChannelFlags],
        channum: int,
        data: bytearray | memoryview,
    ) -> ChannelFlags:
        return ChannelFlags(
            channum=channum,
            hide_channel=bool(data[0] & 0b10000000),
            skip=(data[0] & 0b01100000) >> 5,
            bank=data[0] & 0b00011111,
            bank_pos=data[1],
            debug_info={"raw": binascii.hexlify(data)} if DEBUG else None,
        )

    def to_data(self, cflags: MutableMemory) -> None:
        # hide_channel, bank
        cflags[0] = (
            bool2bit(self.hide_channel, 0b10000000)
            | ((self.skip & 0b11) << 5)
            | (self.bank & 0b00011111)
        )
        # bank_pos
        cflags[1] = self.bank_pos


@dataclass
class Channel:
    number: int

    freq: int
    freq_flags: int
    name: str
    mode: int
    af_filter: bool
    attenuator: bool
    tuning_step: int
    duplex: int
    # duplex offset
    offset: int
    # tone
    tone_mode: int
    # tsql freq
    tsql_freq: int
    # dtcs code
    dtcs: int
    # dtcs polarity
    polarity: int
    vsc: bool

    canceller: int
    canceller_freq: int

    # control flags
    hide_channel: bool
    skip: int
    # 31 = no bank
    bank: int
    bank_pos: int

    debug_info: dict[str, object] | None = None
    updated: bool = False

    @property
    def active(self) -> bool:
        return self.freq != 0 and not self.hide_channel

    def delete(self) -> None:
        self.freq = 0
        self.hide_channel = True
        self.bank = consts.BANK_NOT_SET

    def clear_bank(self) -> None:
        self.bank = consts.BANK_NOT_SET
        self.bank_pos = 0

    @property
    def hidden(self) -> bool:
        return self.hide_channel or self.freq == 0

    def __str__(self) -> str:
        try:
            bank = f"{consts.BANK_NAMES[self.bank]}/{self.bank_pos}"
        except IndexError:
            bank = f"{self.bank}/{self.bank_pos}"

        return (
            f"Channel {id(self)}-{self.number}: "
            f"f={self.freq}, "
            f"ff={self.freq_flags} ({self.freq_flags:>04b}), "
            f"af={self.af_filter}, "
            f"att={self.attenuator}, "
            f"mode={consts.MODES[self.mode]}, "
            "tuning_step="
            f"{self.tuning_step}:{consts.STEPS[self.tuning_step]}, "
            f"duplex={consts.DUPLEX_DIRS[self.duplex]}, "
            f"tone_mode={consts.TONE_MODES[self.tone_mode]}, "
            f"offset={self.offset}, "
            f"tsql_freq={_try_get(consts.CTCSS_TONES, self.tsql_freq)}, "
            f"dtcs={_try_get(consts.DTCS_CODES, self.dtcs)}, "
            f"cf={self.canceller_freq}, "
            f"vsc={self.vsc}, "
            f"c={self.canceller}, "
            f"name={self.name!r}, "
            f"hide={self.hide_channel}, "
            f"skip={consts.SKIPS[self.skip]}, "
            f"polarity={consts.POLARITY[self.polarity]}, "
            f"bank={bank}, "
            f"debug_info={self.debug_info} "
        )

    def __lt__(self, other: object) -> bool:
        assert isinstance(other, Channel)
        return self.number < other.number

    def clone(self) -> Channel:
        return copy.deepcopy(self)

    @classmethod
    def from_data(
        cls: type[Channel],
        idx: int,
        data: bytearray | memoryview,
        cflags: bytearray | memoryview | None,
    ) -> Channel:
        freq = ((data[2] & 0b00000011) << 16) | (data[1] << 8) | data[0]
        freq_flags = (data[2] & 0b11110000) >> 4
        offset = (data[6] << 8) | data[5]

        freq_real = offset_real = 0
        try:
            freq_real = coding.decode_freq(freq, freq_flags & 0b11)
            offset_real = coding.decode_freq(offset, freq_flags >> 2)
        except ValueError as err:
            _LOG.error(
                "decode freq error: %r, idx=%d, data=%r, cdata=%r, "
                "freq=%r, offset=%r, flags=%r",
                err,
                idx,
                data,
                cflags,
                freq,
                offset,
                data[2],
            )

        debug_info = (
            {
                "unknowns": [
                    data[4] & 0b11000000,  # always 0
                    data[4] & 0b00001000,  # 0 for valid channels
                    data[7] & 0b11000000,  # 0 for valid channels
                    data[10] & 0b01111000,  # always 0
                ],
                "raw": binascii.hexlify(bytes(data)),
                "raw_flags": binascii.hexlify(bytes(cflags))
                if cflags
                else None,
                "freq": freq,
                "offset": offset,
                "flags": (data[2] & 0b11110000) >> 4,
            }
            if DEBUG
            else None
        )

        if cflags:
            hide_channel = cflags[0] & 0b10000000
            skip = (cflags[0] & 0b01100000) >> 5
            bank = cflags[0] & 0b00011111
            bank_pos = cflags[1]
        else:
            hide_channel = skip = bank = bank_pos = 0

        duplex = d if (d := (data[4] & 0b00110000) >> 4) <= 2 else 0
        tone_mode = t if (t := data[4] & 0b00000111) <= 4 else 0
        tsql_freq = (
            ts if (ts := data[7] & 0b00111111) < len(consts.CTCSS_TONES) else 0
        )
        dtcs = d if (d := data[8] & 0b01111111) < len(consts.DTCS_CODES) else 0
        vsc = bool(data[10] & 0b00000100)
        return Channel(
            number=idx,
            freq=freq_real,
            freq_flags=freq_flags,
            af_filter=bool(data[3] & 0b10000000),
            attenuator=bool(data[3] & 0b01000000),
            mode=(data[3] & 0b00110000) >> 4,
            tuning_step=data[3] & 0b00001111,
            duplex=duplex,
            tone_mode=tone_mode,
            offset=offset_real,
            tsql_freq=tsql_freq,
            polarity=(data[8] & 0b10000000) >> 7,
            dtcs=dtcs,
            canceller_freq=10
            * ((data[9] << 1) | ((data[10] & 0b10000000) >> 7)),
            vsc=vsc,
            canceller=0 if vsc else (data[10] & 0b00000011),
            name=coding.decode_name(data[11:16]),
            hide_channel=bool(hide_channel),
            skip=skip,
            bank=bank,
            bank_pos=bank_pos,
            debug_info=debug_info,  # type: ignore
        )

    def to_data(self, data: MutableMemory, cflags: MutableMemory) -> None:
        self.offset = min(self.offset, consts.MAX_OFFSET)

        enc_freq = coding.encode_freq(self.freq, self.offset)
        freq0, freq1, freq2 = enc_freq.freq_bytes()
        offset_l, offset_h = enc_freq.offset_bytes()

        # freq
        data[0] = freq0
        data[1] = freq1
        # flags & freq2
        data_set(data, 2, 0b11110000, enc_freq.flags << 4)
        data_set(data, 2, 0b00001111, freq2 & 0b1111)
        # af_filter, attenuator, mode, tuning_step
        data[3] = (
            bool2bit(self.af_filter, 0b10000000)
            | bool2bit(self.attenuator, 0b01000000)
            | (self.mode & 0b11) << 4
            | (self.tuning_step & 0b1111)
        )
        # duplex
        duplex = self.duplex if self.duplex <= 2 else 0
        data_set(data, 4, 0b00110000, duplex << 4)
        # must be set to zero?
        data_set(data, 4, 0b00001000, 0)
        # tone_mode
        data_set(data, 4, 0b00000111, self.tone_mode)
        # offset
        data[5] = offset_l
        data[6] = offset_h

        # must be set to zero?
        data_set(data, 7, 0b11000000, 0)
        # tsql_freq
        data_set(data, 7, 0b00111111, min(self.tsql_freq, 49))
        # polarity, dtcs
        data[8] = bool2bit(self.polarity, 0b10000000) | (
            self.dtcs & 0b01111111
        )
        # canceller freq
        canc_freq = self.canceller_freq // 10
        data[9] = (canc_freq & 0b111111110) >> 1
        data_set(data, 10, 0b10000000, (canc_freq & 1) << 7)
        # vsc & canceller
        if self.vsc:
            # set vsc, disable canceller
            data_set(data, 10, 0b00000111, 0b100)
        elif self.canceller:
            # set canceller; set vsc to 0
            data_set(data, 10, 0b111, self.canceller & 0b11)
        else:
            # disable vsc & canceller
            data_set(data, 10, 0b111, 0)

        # name
        data[11:16] = bytes(coding.encode_name(self.name))

        # hide_channel, bank
        cflags[0] = (
            bool2bit(self.hide_channel, 0b10000000)
            | ((self.skip & 0b11) << 5)
            | (self.bank & 0b00011111)
        )
        # bank_pos
        cflags[1] = self.bank_pos

    def validate(self) -> None:
        if not validators.validate_frequency(self.freq):
            raise ValidateError("freq", self.freq)

        _is_valid_index(consts.MODES, self.mode, "mode")
        _is_valid_index(consts.STEPS, self.tuning_step, "tuning step")
        _is_valid_index(consts.SKIPS, self.skip, "skip")

        _is_valid_index(consts.DUPLEX_DIRS, self.duplex, "duplex")
        if not validators.validate_offset(self.freq, self.offset):
            raise ValidateError("offset", self.offset)

        _is_valid_index(consts.TONE_MODES, self.tone_mode, "tone mode")
        # TSQL
        _is_valid_index(consts.CTCSS_TONES, self.tsql_freq, "tsql freq")
        _is_valid_index(consts.DTCS_CODES, self.dtcs, "dtcs")
        _is_valid_index(consts.POLARITY, self.polarity, "polarity")

        if self.bank < 0 or (
            self.bank != consts.BANK_NOT_SET and self.bank >= consts.NUM_BANKS
        ):
            raise ValidateError("bank", self.bank)

        try:
            validators.validate_name(self.name)
        except ValueError as err:
            raise ValidateError("name", self.name) from err

    def to_record(self) -> dict[str, object]:
        if self.hide_channel:
            return {}

        try:
            bank = consts.BANK_NAMES[self.bank]
        except IndexError:
            bank = ""

        return {
            "channel": self.number,
            "freq": self.freq,
            "af": self.af_filter,
            "att": self.attenuator,
            "mode": consts.MODES[self.mode],
            "ts": consts.STEPS[self.tuning_step],
            "dup": consts.DUPLEX_DIRS[self.duplex],
            "tone_mode": consts.TONE_MODES[self.tone_mode],
            "offset": self.offset,
            "tsql_freq": _try_get(consts.CTCSS_TONES, self.tsql_freq),
            "dtcs": _try_get(consts.DTCS_CODES, self.dtcs),
            "canceller freq": self.canceller_freq,
            "vsc": self.vsc,
            "canceller": consts.CANCELLER[self.canceller],
            "name": self.name,
            "hide": self.hide_channel,
            "skip": consts.SKIPS[self.skip],
            "polarity": consts.POLARITY[self.polarity],
            "bank": bank,
            "bank_pos": self.bank_pos if bank else "",
        }

    def from_record(self, data: dict[str, object]) -> None:  # noqa: PLR0912,C901
        _LOG.debug("from_record: %r", data)
        if (freq := data.get("freq")) is not None:
            ifreq = int(freq or "0")  # type: ignore
            self.freq = fixers.fix_frequency(ifreq) if ifreq else 0
            self.hide_channel = not self.freq

        if (af := data.get("af")) is not None:
            self.af_filter = obj2bool(af)

        if (att := data.get("att")) is not None:
            self.attenuator = obj2bool(att)

        if (mode := data.get("mode")) is not None:
            self.mode = get_index_or_default(consts.MODES, mode, 4)

        if (ts := data.get("ts")) is not None:
            self.tuning_step = get_index_or_default(consts.STEPS, ts, 14)

        if (dup := data.get("dup")) is not None:
            self.duplex = get_index_or_default(consts.DUPLEX_DIRS, dup)

        if (mode := data.get("tone_mode")) is not None:
            self.tone_mode = get_index_or_default(consts.TONE_MODES, mode)

        if (offset := data.get("offset")) is not None:
            off = int(offset)  # type: ignore
            self.offset = fixers.fix_offset(self.freq, off) if off else 0

        if (tf := data.get("tsql_freq")) is not None:
            self.tsql_freq = get_index_or_default(consts.CTCSS_TONES, tf)

        if (dtcs := data.get("dtcs")) is not None:
            self.dtcs = get_index_or_default(consts.DTCS_CODES, dtcs)

        if (cf := data.get("canceller freq")) is not None:
            self.canceller_freq = int(cf or 300)  # type: ignore

        if (c := data.get("canceller")) is not None:
            self.canceller = get_index_or_default(consts.CANCELLER, c)
            if self.canceller:
                self.vsc = False

        if (vsc := data.get("vsc")) is not None:
            self.vsc = obj2bool(vsc)
            if self.vsc:
                self.canceller = 0

        if (n := data.get("name")) is not None:
            self.name = fixers.fix_name(str(n))

        if (s := data.get("skip")) is not None:
            self.skip = get_index_or_default(consts.SKIPS, s)

        if (p := data.get("polarity")) is not None:
            self.polarity = get_index_or_default(consts.POLARITY, p)

        if (bank := data.get("bank")) is not None:
            self.bank = get_index_or_default(
                consts.BANK_NAMES, bank, consts.BANK_NOT_SET
            )

        if (bp := data.get("bank_pos")) is not None and bp != "":
            self.bank_pos = int(bp)  # type: ignore

    def load_defaults(self, freq: int | None = None) -> None:
        if freq is None:
            freq = self.freq

        self.name = ""
        self.mode = consts.default_mode_for_freq(freq) if freq else 0
        self.af_filter = False
        self.attenuator = False
        self.tuning_step = consts.default_tuning_step_for_freq(freq)
        self.duplex = 0
        self.offset = 0
        self.tone_mode = 0
        self.tsql_freq = 0
        self.dtcs = 0
        self.polarity = 0
        self.vsc = False
        self.skip = 0

    def load_defaults_from_band(self, band: BandDefaults) -> None:
        self.name = ""
        self.mode = band.mode
        self.af_filter = band.af_filter
        self.attenuator = band.attenuator
        self.tuning_step = band.tuning_step
        self.duplex = band.duplex
        self.offset = band.offset
        self.tone_mode = band.tone_mode
        self.tsql_freq = band.tsql_freq
        self.dtcs = band.dtcs
        self.polarity = band.polarity
        self.vsc = band.vsc
        self.skip = 0
        self.canceller = band.canceller
        self.canceller_freq = band.canceller_freq


@dataclass
class BankChannels:
    channels: list[int | None] = field(default_factory=lambda: [None] * 100)

    def __getitem__(self, pos: int) -> int | None:
        return self.channels[pos]

    def __contains__(self, channum: int) -> bool:
        return channum in self.channels

    def index(self, channum: int) -> int:
        return self.channels.index(channum)

    def find_free_slot(self, start: int = 0) -> int | None:
        assert self.channels is not None
        for idx in range(start, len(self.channels)):
            if self.channels[idx] is None:
                return idx

        return None

    def set(self, channels: ty.Iterable[Channel]) -> None:
        chs = self.channels
        for chan in channels:
            if chs[chan.bank_pos] is None:
                chs[chan.bank_pos] = chan.number
            else:
                _LOG.debug(
                    "duplicated channel in bank on pos: %d", chan.bank_pos
                )


@dataclass
class Bank:
    idx: int
    # 6 characters
    name: str

    debug_info: dict[str, object] | None = None

    def clone(self) -> Bank:
        return copy.deepcopy(self)

    @classmethod
    def from_data(
        cls: type[Bank], idx: int, data: bytearray | memoryview
    ) -> Bank:
        return Bank(
            idx,
            name=bytes(data[0:6]).decode() if data[0] else "",
            debug_info={"raw": binascii.hexlify(data)} if DEBUG else None,
        )

    def to_data(self, data: MutableMemory) -> None:
        data[0:6] = self.name[:6].ljust(6).encode()


@dataclass
class ScanLink:
    idx: int
    name: str
    edges: int

    debug_info: dict[str, object] | None = None

    def links(self) -> ty.Iterable[bool]:
        for idx in range(consts.NUM_SCAN_EDGES):
            yield bool(self.edges & (1 << idx))

    def __getitem__(self, idx: int) -> bool:
        if idx < 0 or idx >= consts.NUM_SCAN_EDGES:
            raise IndexError

        return bool(self.edges & (1 << idx))

    def __setitem__(self, idx: int, value: object) -> None:
        if idx < 0 or idx >= consts.NUM_SCAN_EDGES:
            raise IndexError

        bit = 1 << idx
        self.edges = (self.edges & (~bit)) | (bit if value else 0)

    def clone(self) -> ScanLink:
        return copy.deepcopy(self)

    @classmethod
    def from_data(
        cls: type[ScanLink],
        idx: int,
        data: bytearray | memoryview,
        edata: bytearray | memoryview,
    ) -> ScanLink:
        # 4 bytes, with 7bite padding = 25 bits
        edges = (
            ((edata[3] & 0b1) << 24)
            | (edata[2] << 16)
            | (edata[1] << 8)
            | edata[0]
        )
        return ScanLink(
            idx=idx,
            name=bytes(data[0:6]).decode() if data[0] else "",
            edges=edges,
            debug_info={"raw": binascii.hexlify(data)} if DEBUG else None,
        )

    def to_data(self, data: MutableMemory, edata: MutableMemory) -> None:
        data[0:6] = self.name[:6].ljust(6).encode()

        edges = self.edges
        edata[0] = edges & 0xFF
        edata[1] = (edges >> 8) & 0xFF
        edata[2] = (edges >> 16) & 0xFF
        edata[3] = ((edges >> 24) & 1) | 0b11111110

    def remap_edges(self, mapping: dict[int, int]) -> None:
        edges = [
            1 if self.edges & (1 << idx) else 0
            for idx in range(consts.NUM_SCAN_EDGES)
        ]

        dst = edges.copy()
        for idst, isrc in mapping.items():
            dst[idst] = edges[isrc]

        res = 0
        for e in reversed(dst):
            res = (res << 1) | e

        self.edges = res


@dataclass
class ScanEdge:
    idx: int
    start: int
    end: int
    mode: int
    # tuning_step include 15 - "-"
    tuning_step: int
    attenuator: int
    name: str

    # from flags
    hidden: bool

    debug_info: dict[str, object] | None = None
    updated: bool = False

    def clone(self) -> ScanEdge:
        return copy.deepcopy(self)

    def delete(self) -> None:
        self.name = ""
        self.start = self.end = 0
        self.attenuator = consts.ATTENUATOR.index("-")
        self.tuning_step = consts.STEPS.index("-")
        self.mode = consts.MODES_SCAN_EDGES.index("-")
        self.hidden = True

    def unhide(self) -> None:
        self.end = self.end or self.start or 1_000_000
        self.start = self.start or self.end or 1_000_000
        self.hidden = False

    @classmethod
    def from_data(
        cls: type[ScanEdge],
        idx: int,
        data: bytearray | memoryview,
        data_flags: bytearray | memoryview,
    ) -> ScanEdge:
        start = (data[3] << 24) | (data[2] << 16) | (data[1] << 8) | data[0]
        start //= 3
        end = (data[7] << 24) | (data[6] << 16) | (data[5] << 8) | data[4]
        end //= 3

        debug_info = (
            {
                "raw": binascii.hexlify(data),
                "raw_flags": binascii.hexlify(data_flags),
                "start_flags_freq": (data[9] >> 2) & 0b11,
                "end_flags_freq": data[9] & 0b11,
            }
            if DEBUG
            else None
        )

        hidden = bool(data_flags[0] >> 7) or not start or not end

        return ScanEdge(
            idx=idx,
            start=start,
            end=end,
            mode=(data[8] & 0b11110000) >> 4,
            tuning_step=(data[8] & 0b00001111),
            attenuator=(data[9] & 0b00110000) >> 4,
            name=bytes(data[10:16]).decode() if data[10] else "",
            hidden=hidden,
            debug_info=debug_info,
        )

    def to_data(self, data: MutableMemory, data_flags: MutableMemory) -> None:
        start = self.start * 3
        data[0] = start & 0xFF
        data[1] = (start >> 8) & 0xFF
        data[2] = (start >> 16) & 0xFF
        data[3] = (start >> 24) & 0xFF

        end = self.end * 3
        data[4] = end & 0xFF
        data[5] = (end >> 8) & 0xFF
        data[6] = (end >> 16) & 0xFF
        data[7] = (end >> 24) & 0xFF

        data[8] = (self.mode & 0b1111) << 4 | (self.tuning_step & 0b1111)

        data_set(data, 9, 0b00110000, self.attenuator << 4)

        if self.name:
            data[10:16] = self.name[:6].ljust(6).encode()
        else:
            data[10:16] = bytes([0, 0, 0, 0, 0, 0])

        if self.hidden:
            data_flags[0] = data_flags[2] = 0xFF
        else:
            data_flags[0] = data_flags[2] = 0x7F

    def validate(self) -> None:
        if self.idx < 0 or self.idx >= consts.NUM_SCAN_EDGES:
            raise ValidateError("idx", self.idx)

        if not validators.validate_frequency(self.start):
            raise ValidateError("idx", self.start)

        if not validators.validate_frequency(self.end):
            raise ValidateError("freq", self.end)

        _is_valid_index(consts.MODES_SCAN_EDGES, self.mode, "mode")
        if self.mode == 3:
            # "auto" is not used
            raise ValidateError("mode", self.mode)

        _is_valid_index(consts.STEPS, self.tuning_step, "tuning step")
        if self.tuning_step == 14:
            # "auto" is not valid
            raise ValidateError("tuning_step", self.tuning_step)

        _is_valid_index(consts.ATTENUATOR, self.attenuator, "attenuator")

        try:
            validators.validate_name(self.name)
        except ValueError as err:
            raise ValidateError("name", self.name) from err

    def to_record(self) -> dict[str, object]:
        return {
            "idx": self.idx,
            "start": self.start,
            "end": self.end,
            "mode": consts.MODES_SCAN_EDGES[self.mode],
            "ts": consts.STEPS[self.tuning_step],
            "att": consts.ATTENUATOR[self.attenuator],
            "name": self.name.rstrip(),
        }

    def from_record(self, data: dict[str, object]) -> None:
        _LOG.debug("from_record: %r", data)
        if (idx := data.get("idx")) is not None:
            self.idx = int(idx)  # type: ignore

        if (start := data.get("start")) is not None:
            self.start = int(start or "0")  # type: ignore

        if (end := data.get("end")) is not None:
            self.end = int(end or "0")  # type: ignore

        if mode := data.get("mode"):
            self.mode = consts.MODES.index(str(mode))
            if self.mode == 3:
                # map "auto" to "-"
                self.mode = 4

        if ts := data.get("ts"):
            self.tuning_step = consts.STEPS.index(str(ts))
            if self.tuning_step == 14:
                # map "auto" tuning_step to "-"
                self.tuning_step = 15

        if att := data.get("att"):
            self.attenuator = get_index_or_default(
                consts.ATTENUATOR, str(att), 2
            )

        if name := data.get("name"):
            self.name = str(name)


@dataclass
class RadioSettings:
    af_filer_am: bool
    af_filer_fm: bool
    af_filer_wfm: bool
    am_ant: int
    auto_power_off: int  # 0 - 6
    backlight: int
    beep_level: int
    charging_type: int  # 0-1
    civ_address: int
    civ_baud_rate: int
    civ_transceive: bool
    dial_function: int  # 0-1
    dial_speed_up: bool
    fm_ant: int
    func_dial_step: int
    key_beep: bool
    key_lock: int  # 0-3
    lcd_contrast: int  # 0-4 -> 1-5
    mem_display_type: int
    monitor: int  # 0=push, 1=hold
    pause_timer: int  # 0-10
    power_save: bool
    program_skip_scan: bool
    resume_timer: int  # 0 -6
    set_expand: bool
    stop_beep: bool

    debug_info: dict[str, object] | None = None
    updated: bool = False

    def clone(self) -> RadioSettings:
        return copy.deepcopy(self)

    @classmethod
    def from_data(
        cls: type[RadioSettings], data: bytearray | memoryview
    ) -> RadioSettings:
        debug_info = (
            {
                "raw": binascii.hexlify(data),
                "priority_scan_type": data[14] & 0b111,
                "scanning_band": data[47],
                "scanning_bank": data[50],
                "scan_enabled": bool(data[52] & 0b01000000),
                "mem_scan_priority": bool(data[52] & 0b00001000),
                "scan_mode": (data[52] & 0b00000100) >> 2,
                "refresh_flag": bool(data[53] & 0b10000000),
                "unprotected_frequency_flag": bool(data[53] & 0b01000000),
                "autowrite_memory": bool(data[53] & 0b00100000),
                "keylock": bool(data[53] & 0b00010000),
                "priority_scan": bool(data[53] & 0b00000010),
                "scan_direction": bool(data[53] & 0b00000001),
                "scan_vfo_type": data[54],
                "scan_mem_type": data[55],
                "mem_chan_data": data[56],
            }
            if DEBUG
            else None
        )

        return RadioSettings(
            func_dial_step=data[13] & 0b00000011,
            key_beep=bool(data[15] & 1),
            beep_level=data[16] & 0b00111111,
            backlight=data[17] & 0b00000011,
            power_save=bool(data[18] & 1),
            am_ant=data[19] & 1,
            fm_ant=data[20] & 1,
            set_expand=bool(data[21] & 1),
            key_lock=data[22] & 0b00000011,
            dial_speed_up=bool(data[23] & 1),
            monitor=data[24] & 1,
            auto_power_off=data[25] & 0b00000111,
            pause_timer=data[26] & 0b00001111,
            resume_timer=data[27] & 0b00000111,
            stop_beep=bool(data[28] & 1),
            lcd_contrast=data[29] & 0b00000111,
            af_filer_fm=bool(data[31] & 1),
            af_filer_wfm=bool(data[32] & 1),
            af_filer_am=bool(data[33] & 1),
            civ_address=data[34],
            civ_baud_rate=data[35] & 0b00000111,
            civ_transceive=bool(data[36] & 1),
            charging_type=data[37] & 1,
            dial_function=(data[52] & 0b00010000) >> 4,
            mem_display_type=data[52] & 0b00000011,
            program_skip_scan=bool(data[53] & 0b00001000),
            debug_info=debug_info,
        )

    def to_data(self, data: MutableMemory) -> None:
        data_set(data, 13, 0b11, self.func_dial_step)
        data_set_bit(data, 15, 0, self.key_beep)
        data_set(data, 16, 0b00111111, self.beep_level)
        data_set(data, 17, 0b11, self.backlight)
        data_set_bit(data, 18, 0, self.power_save)
        data_set_bit(data, 19, 0, self.am_ant)
        data_set_bit(data, 20, 0, self.fm_ant)
        data_set_bit(data, 21, 0, self.set_expand)
        data_set(data, 22, 0b11, self.key_lock)
        data_set_bit(data, 23, 0, self.dial_speed_up)
        data_set_bit(data, 24, 0, self.monitor)
        data_set(data, 25, 0b111, self.auto_power_off)
        data_set(data, 26, 0b1111, self.pause_timer)
        data_set(data, 27, 0b111, self.resume_timer)
        data_set_bit(data, 28, 0, self.stop_beep)
        data_set(data, 29, 0b111, self.lcd_contrast)
        data_set_bit(data, 31, 0, self.af_filer_fm)
        data_set_bit(data, 32, 0, self.af_filer_wfm)
        data_set_bit(data, 33, 0, self.af_filer_am)
        data[34] = self.civ_address
        data_set(data, 35, 0b00000111, self.civ_baud_rate)
        data_set_bit(data, 36, 0, self.civ_transceive)
        data_set_bit(data, 37, 0, self.charging_type)
        data_set_bit(data, 52, 4, self.dial_function)
        data_set(data, 52, 0b11, self.mem_display_type)
        data_set_bit(data, 53, 3, self.program_skip_scan)


@dataclass
class BankLinks:
    banks: int

    def __str__(self) -> str:
        return f"<BankLinks: {self.human()}>"

    def __getitem__(self, idx: int) -> bool:
        return bool(self.banks & (1 << idx))

    def __setitem__(self, idx: int, value: object) -> None:
        bit = 1 << idx
        self.banks = (self.banks & (~bit)) | (bit if value else 0)

    def clone(self) -> BankLinks:
        return BankLinks(self.banks)

    def bits(self) -> ty.Iterable[bool]:
        return (bool(self.banks & (1 << i)) for i in range(consts.NUM_BANKS))

    @classmethod
    def from_data(
        cls: type[BankLinks], data: bytearray | memoryview
    ) -> BankLinks:
        # Y -> A
        assert len(data) == 3
        banks = ((data[2] & 0b00111111) << 16) | (data[1] << 8) | data[0]
        return BankLinks(banks)

    def to_data(self, data: MutableMemory) -> None:
        val = self.banks
        data[0] = val & 0xFF
        data[1] = (val >> 8) & 0xFF
        data[2] = (data[2] & 0b11000000) | ((val >> 16) & 0b111111)

    def human(self) -> str:
        return "".join(
            bn if self.banks & (1 << idx) else " "
            for idx, bn in enumerate(consts.BANK_NAMES)
        )


@dataclass
class BandDefaults:
    idx: int
    freq: int
    offset: int
    tuning_step: int
    tsql_freq: int
    dtcs: int
    mode: int
    canceller_freq: int
    duplex: int
    tone_mode: int
    vsc: bool
    canceller: int
    polarity: int
    af_filter: bool
    attenuator: bool

    debug_info: dict[str, object] | None

    @classmethod
    def from_data(
        cls: type[BandDefaults],
        idx: int,
        data: bytearray | memoryview,
    ) -> BandDefaults:
        freq = (data[3] << 24) | (data[2] << 16) | (data[1] << 8) | data[0]
        freq //= 3
        offset = (data[7] << 24) | (data[6] << 16) | (data[5] << 8) | data[4]
        offset //= 3

        debug_info = (
            {
                "raw": binascii.hexlify(data),
                "unknown6": data[11],
            }
            if DEBUG
            else None
        )

        return BandDefaults(
            idx=idx,
            freq=freq,
            offset=offset,
            tuning_step=data[8] & 0b1111,
            tsql_freq=data[9] & 0b111111,
            dtcs=data[10] & 0b01111111,
            mode=(data[12] & 0b00110000) >> 4,
            canceller_freq=(data[14] << 8) | data[15],
            duplex=(data[12] >> 6),
            tone_mode=data[12] & 0b1111,
            vsc=bool(data[13] & 0b01000000),
            canceller=(data[13] & 0b00110000) >> 4,
            polarity=(data[13] & 0b00000100) >> 2,
            af_filter=bool(data[13] & 0b00000010),
            attenuator=bool(data[13] & 0b0000001),
            debug_info=debug_info,
        )

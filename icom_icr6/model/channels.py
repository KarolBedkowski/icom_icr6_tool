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
from dataclasses import dataclass, field

from icom_icr6 import coding, consts, fixers, validators

from ._support import (
    DEBUG,
    MutableMemory,
    ValidateError,
    bool2bit,
    data_set,
    get_index_or_default,
    is_valid_index,
    obj2bool,
    try_get,
)

if ty.TYPE_CHECKING:
    from .settings import BandDefaults

_LOG = logging.getLogger(__name__)


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
    # hack; skips on two bits (skip type (S/P) and skip enable (0/1))
    # should be 2 fields
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
            f"tsql_freq={try_get(consts.CTCSS_TONES, self.tsql_freq)}, "
            f"dtcs={try_get(consts.DTCS_CODES, self.dtcs)}, "
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

        is_valid_index(consts.MODES, self.mode, "mode")
        is_valid_index(consts.STEPS, self.tuning_step, "tuning step")
        is_valid_index(consts.SKIPS, self.skip, "skip")

        is_valid_index(consts.DUPLEX_DIRS, self.duplex, "duplex")
        if not validators.validate_offset(self.freq, self.offset):
            raise ValidateError("offset", self.offset)

        is_valid_index(consts.TONE_MODES, self.tone_mode, "tone mode")
        # TSQL
        is_valid_index(consts.CTCSS_TONES, self.tsql_freq, "tsql freq")
        is_valid_index(consts.DTCS_CODES, self.dtcs, "dtcs")
        is_valid_index(consts.POLARITY, self.polarity, "polarity")

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
            "tsql_freq": try_get(consts.CTCSS_TONES, self.tsql_freq),
            "dtcs": try_get(consts.DTCS_CODES, self.dtcs),
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

    def from_record(self, data: dict[str, object]) -> None:  # noqa: PLR0912,C901 pylint:disable=too-many-branches
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

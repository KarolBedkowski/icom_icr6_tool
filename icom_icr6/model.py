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
import unicodedata
from collections import abc
from dataclasses import dataclass, field

from . import consts

_LOG = logging.getLogger(__name__)


MutableMemory = abc.MutableSequence[int] | memoryview


@dataclass
class RadioModel:
    # Data format - 39B
    # mode: 4B
    # rev: 1B
    # comment: 16B
    # unknown: 4B
    # serial 14B
    model: bytes
    rev: int
    comment: str
    serial: str

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

        return RadioModel(
            model=bytes(data[0:4]),
            rev=data[5],
            comment=bytes(data[6:22]).decode(),
            serial=serial_decoded,
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


class ValidateError(ValueError):
    def __init__(self, field: str, value: object) -> None:
        self.field = field
        self.value = value

    def __str__(self) -> str:
        return "invalid value in {self.field}: {self.value!r}"


@dataclass
class ChannelFlags:
    channum: int
    # control flags
    hide_channel: bool
    skip: int
    # 31 = no bank
    bank: int
    bank_pos: int

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
        )


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
    # dtsc code
    dtsc: int
    # dtsc polarity
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

    def delete(self) -> None:
        self.freq = 0
        self.hide_channel = True

    def clear_bank(self) -> None:
        self.bank = consts.BANK_NOT_SET
        self.bank_pos = 0

    def __str__(self) -> str:
        try:
            bank = f"{consts.BANK_NAMES[self.bank]}/{self.bank_pos}"
        except IndexError:
            bank = f"{self.bank}/{self.bank_pos}"

        return (
            f"Channel {self.number}: "
            f"f={self.freq}, "
            f"ff={self.freq_flags}, "
            f"af={self.af_filter}, "
            f"att={self.attenuator}, "
            f"mode={consts.MODES[self.mode]}, "
            f"tuning_step={consts.STEPS[self.tuning_step]}, "
            f"duplex={consts.DUPLEX_DIRS[self.duplex]}, "
            f"tone_mode={consts.TONE_MODES[self.tone_mode]}, "
            f"offset={self.offset}, "
            f"tsql_freq={_try_get(consts.CTCSS_TONES, self.tsql_freq)}, "
            f"dtsc={_try_get(consts.DTCS_CODES, self.dtsc)}, "
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
            freq_real = decode_freq(freq, freq_flags & 0b11)
            offset_real = decode_freq(offset, freq_flags >> 2)
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

        debug_info = {
            "unknowns": [
                data[4] & 0b11000000,
                data[4] & 0b00001000,  # TODO: flag "is channel valid"?
                data[7] & 0b11111110,
                data[10] & 0b01111000,
            ],
            "raw": binascii.hexlify(bytes(data)),
            "freq": freq,
            "offset": offset,
            "flags": (data[2] & 0b11110000) >> 4,
        }

        if cflags:
            hide_channel = cflags[0] & 0b10000000
            skip = (cflags[0] & 0b01100000) >> 5
            bank = cflags[0] & 0b00011111  # TODO: verify
            bank_pos = cflags[1]  # TODO: verify
        else:
            hide_channel = skip = bank = bank_pos = 0

        return Channel(
            number=idx,
            freq=freq_real,
            freq_flags=freq_flags,
            af_filter=bool(data[3] & 0b10000000),
            attenuator=bool(data[3] & 0b01000000),
            mode=(data[3] & 0b00110000) >> 4,
            tuning_step=data[3] & 0b00001111,
            duplex=(data[4] & 0b00110000) >> 4,
            tone_mode=data[4] & 0b00000111,
            offset=offset_real,
            tsql_freq=data[7] & 0b00111111,
            polarity=(data[8] & 0b10000000) >> 7,
            dtsc=(data[8] & 0b01111111),
            canceller_freq=(data[9] << 1) | ((data[10] & 0b10000000) >> 7),
            vsc=bool(data[10] & 0b00000100),
            canceller=data[10] & 0b00000011,
            name=decode_name(data[11:16]),
            hide_channel=bool(hide_channel),
            skip=skip,
            bank=bank,
            bank_pos=bank_pos,
            debug_info=debug_info,
        )

    def to_data(self, data: MutableMemory, cflags: MutableMemory) -> None:
        enc_freq = encode_freq(self.freq, self.offset)
        freq0, freq1, freq2 = enc_freq.freq_bytes()
        offset_l, offset_h = enc_freq.offset_bytes()

        # freq
        data[0] = freq0
        data[1] = freq1
        # flags & freq2
        data_set(data, 2, 0b11110000, enc_freq.flags << 4)
        data_set(data, 2, 0b00001111, freq2 & 0b1111)
        print(repr(enc_freq), bin(data[2]))
        # af_filter, attenuator, mode, tuning_step
        data[3] = (
            bool2bit(self.af_filter, 0b10000000)
            | bool2bit(self.attenuator, 0b01000000)
            | (self.mode & 0b11) << 4
            | (self.tuning_step & 0b1111)
        )
        # duplex
        data_set(data, 4, 0b00110000, self.duplex << 4)
        # tone_mode
        data_set(data, 4, 0b00000111, self.tone_mode)
        # offset
        data[5] = offset_l
        data[6] = offset_h
        # tsql_freq
        data_set(data, 7, 0b00111111, self.tsql_freq)
        # polarity, dtsc
        data[8] = bool2bit(self.polarity, 0b10000000) | (
            self.dtsc & 0b01111111
        )
        # canceller freq
        data[9] = (self.canceller_freq & 0b111111110) >> 1
        data_set(data, 10, 0b10000000, (self.canceller_freq & 1) << 7)
        # vsc
        data_set(data, 10, 0b00000100, self.vsc << 3)
        # canceller
        data_set(data, 10, 0b11, self.canceller)
        # name
        data[11:16] = bytes(encode_name(self.name))

        # hide_channel, bank
        cflags[0] = (
            bool2bit(self.hide_channel, 0b10000000)
            | ((self.skip & 0b11) << 5)
            | (self.bank & 0b00011111)
        )
        # bank_pos
        cflags[1] = self.bank_pos

    def validate(self) -> None:
        if not validate_frequency(self.freq):
            raise ValidateError("freq", self.freq)

        _is_valid_index(consts.MODES, self.mode, "mode")
        _is_valid_index(consts.STEPS, self.tuning_step, "tuning step")
        _is_valid_index(consts.SKIPS, self.skip, "skip")

        _is_valid_index(consts.DUPLEX_DIRS, self.duplex, "duplex")
        if self.duplex in (1, 2) and not validate_offset(self.offset):
            raise ValidateError("offset", self.offset)

        _is_valid_index(consts.TONE_MODES, self.tone_mode, "tone mode")
        if self.tone_mode in (1, 2):  # TSQL
            _is_valid_index(consts.CTCSS_TONES, self.tsql_freq, "tsql freq")
        elif self.tone_mode in (3, 4):
            _is_valid_index(consts.DTCS_CODES, self.dtsc, "dtsc")
            _is_valid_index(consts.POLARITY, self.polarity, "polarity")

        if self.bank < 0 or (
            self.bank != consts.BANK_NOT_SET and self.bank >= consts.NUM_BANKS
        ):
            raise ValidateError("bank", self.bank)

        try:
            validate_name(self.name)
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
            "af": str(self.af_filter),
            "att": str(self.attenuator),
            "mode": consts.MODES[self.mode],
            "ts": consts.STEPS[self.tuning_step],
            "dup": consts.DUPLEX_DIRS[self.duplex],
            "tone_mode": consts.TONE_MODES[self.tone_mode],
            "offset": self.offset,
            "tsql_freq": _try_get(consts.CTCSS_TONES, self.tsql_freq),
            "dtsc": _try_get(consts.DTCS_CODES, self.dtsc),
            "cf": self.canceller_freq,
            "vsc": str(self.vsc),
            "c": self.canceller,
            "name": self.name,
            "hide": self.hide_channel,
            "skip": consts.SKIPS[self.skip],
            "polarity": consts.POLARITY[self.polarity],
            "bank": bank,
            "bank_pos": self.bank_pos if bank else "",
        }

    def from_record(self, data: dict[str, object]) -> None:
        # TODO: adjust freq
        _LOG.debug("data: %r", data)
        self.freq = int(data["freq"] or "0")  # type: ignore
        self.af_filter = obj2bool(data["af"])
        self.attenuator = obj2bool(data["att"])
        self.mode = consts.MODES.index(str(data["mode"]))
        self.tuning_step = consts.STEPS.index(str(data["ts"]))
        self.duplex = consts.DUPLEX_DIRS.index(str(data["dup"]))
        self.tone_mode = consts.TONE_MODES.index(str(data["tone_mode"]))
        self.offset = int(data["offset"])  # type: ignore
        self.tsql_freq = consts.CTCSS_TONES.index(str(data["tsql_freq"]))
        self.dtsc = consts.DTCS_CODES.index(str(data["dtsc"]))
        self.canceller_freq = int(data["cf"])  # type: ignore
        self.vsc = obj2bool(data["vsc"])
        self.canceller = int(data["c"])  # type: ignore
        self.name = str(data["name"])
        self.skip = consts.SKIPS.index(str(data["skip"]))
        self.polarity = consts.POLARITY.index(str(data["polarity"]))
        if bank := data["bank"]:
            self.bank = consts.BANK_NAMES.index(ty.cast(str, bank))
            self.bank_pos = int(ty.cast(str, data["bank_pos"]))
        else:
            self.bank = consts.BANK_NOT_SET
            self.bank_pos = 0

        if self.freq:
            self.hide_channel = False


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

    def set(self, chan_flags: ty.Iterable[ChannelFlags]) -> None:
        for cf in chan_flags:
            self.channels[cf.bank_pos] = cf.channum


@dataclass
class Bank:
    idx: int
    # 6 characters
    name: str

    @classmethod
    def from_data(cls: type[Bank], idx: int, data: abc.Sequence[int]) -> Bank:
        return Bank(
            idx,
            name=bytes(data[0:6]).decode() if data[0] else "",
        )

    def to_data(self, data: MutableMemory) -> None:
        data[0:6] = self.name[:6].ljust(6).encode()


@dataclass
class ScanLink:
    idx: int
    name: str
    edges: int

    def __getitem__(self, idx: int) -> bool:
        if idx < 0 or idx >= consts.NUM_SCAN_EDGES:
            raise IndexError

        return bool(self.edges & (1 << idx))

    def __setitem__(self, idx: int, value: object) -> None:
        if idx < 0 or idx >= consts.NUM_SCAN_EDGES:
            raise IndexError

        bit = 1 << idx
        self.edges = (self.edges & (~bit)) | (bit if value else 0)

    @classmethod
    def from_data(
        cls: type[ScanLink],
        idx: int,
        data: abc.Sequence[int],
        edata: abc.Sequence[int],
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
        )

    def to_data(self, data: MutableMemory, edata: MutableMemory) -> None:
        data[0:6] = self.name[:6].ljust(6).encode()

        edges = self.edges
        edata[0] = edges & 0xFF
        edata[1] = (edges >> 8) & 0xFF
        edata[2] = (edges >> 16) & 0xFF
        edata[3] = (edges >> 24) & 0xFF


@dataclass
class ScanEdge:
    idx: int
    start: int
    end: int
    # TODO: check - always False
    disabled: int
    mode: int
    tuning_step: int
    attenuator: int
    name: str

    def human_attn(self) -> str:
        match self.attenuator:
            case 0:
                return "Off"
            case 1:
                return "On"
            case 2:
                return "-"

        return str(self.attenuator)

    def clone(self) -> ScanEdge:
        return copy.deepcopy(self)

    def delete(self) -> None:
        self.name = ""
        self.start = self.end = 0

    @classmethod
    def from_data(
        cls: type[ScanEdge], idx: int, data: abc.Sequence[int]
    ) -> ScanEdge:
        start = (data[3] << 24) | (data[2] << 16) | (data[1] << 8) | data[0]
        start //= 3
        end = (data[7] << 24) | (data[6] << 16) | (data[5] << 8) | data[4]
        end //= 3

        return ScanEdge(
            idx=idx,
            start=start,
            end=end,
            disabled=bool(data[8] & 0b10000000),
            mode=(data[8] & 0b01110000) >> 4,
            tuning_step=(data[8] & 0b00001111),
            attenuator=(data[9] & 0b00110000) >> 4,
            name=bytes(data[10:16]).decode() if data[10] else "",
        )

    def to_data(self, data: MutableMemory) -> None:
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

        data[8] = (
            bool2bit(self.disabled, 0b10000000)
            | (self.mode & 0b111) << 4
            | (self.tuning_step & 0b1111)
        )

        data_set(data, 9, 0b00110000, self.attenuator << 4)

        if self.name:
            data[10:16] = self.name[:6].ljust(6).encode()
        else:
            data[10:16] = bytes([0, 0, 0, 0, 0, 0])

    def validate(self) -> None:
        if self.idx < 0 or self.idx >= consts.NUM_SCAN_EDGES:
            raise ValidateError("idx", self.idx)

        if not validate_frequency(self.start):
            raise ValidateError("idx", self.start)

        if not validate_frequency(self.end):
            raise ValidateError("freq", self.end)

        _is_valid_index(consts.MODES, self.mode, "mode")
        _is_valid_index(consts.STEPS, self.tuning_step, "tuning step")

        try:
            validate_name(self.name)
        except ValueError as err:
            raise ValidateError("name", self.name) from err

    def to_record(self) -> dict[str, object]:
        return {
            "idx": self.idx,
            "start": self.start,
            "end": self.end,
            "mode": consts.MODES[self.mode],
            "ts": consts.STEPS[self.tuning_step],
            "att": str(self.attenuator),
            "name": self.name,
        }

    def from_record(self, data: dict[str, object]) -> None:
        _LOG.debug("data: %r", data)
        self.idx = int(data["idx"])  # type: ignore
        self.start = int(data["start"] or "0")  # type: ignore
        self.end = int(data["end"] or "0")  # type: ignore
        self.mode = consts.MODES.index(str(data["mode"]))
        self.tuning_step = consts.STEPS.index(str(data["ts"]))
        self.attenuator = obj2bool(data["att"])
        self.name = str(data["name"])


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

    @classmethod
    def from_data(
        cls: type[RadioSettings], data: abc.Sequence[int]
    ) -> RadioSettings:
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


class RadioMemory:
    def __init__(self) -> None:
        self.mem = bytearray(consts.MEM_SIZE)
        self.file_comment = ""
        self.file_maprev = "1"
        # 001A = EU, 0003 = USA, 0002A - ?
        # for USA - canceller is available
        self.file_etcdata = "001A"

    def reset(self) -> None:
        pass

    def update_from(self, rm: RadioMemory) -> None:
        self.mem = rm.mem
        self.file_comment = rm.file_comment
        self.file_maprev = rm.file_maprev
        self.file_etcdata = rm.file_etcdata
        self.validate()
        self.reset()

    def update(self, addr: int, length: int, data: bytes) -> None:
        assert len(data) == length
        self.mem[addr : addr + length] = data

    def dump(self, step: int = 16) -> ty.Iterator[str]:
        """Dump data in icf file format."""
        for idx in range(0, 0x6E60, step):
            data = self.mem[idx : idx + step]
            data_hex = binascii.hexlify(bytes(data)).decode()
            res = f"{idx:04x}{step:02x}{data_hex}"
            yield res.upper()

    def read(self, line: str) -> None:
        """Read line from icf file"""
        addr = int(line[0:4], 16)
        size = int(line[4:6], 16)
        data_raw = line[6:]
        assert size * 2 == len(data_raw)
        data = binascii.unhexlify(data_raw)
        self.mem[addr : addr + size] = data

    def validate(self) -> None:
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

    def get_channel(self, idx: int) -> Channel:
        if idx < 0 or idx > consts.NUM_CHANNELS - 1:
            raise IndexError

        start = idx * 16
        cflags_start = idx * 2 + 0x5F80

        return Channel.from_data(
            idx,
            self.mem[start : start + 16],
            self.mem[cflags_start : cflags_start + 2],
        )

    def set_channel(self, chan: Channel) -> None:
        _LOG.debug("set_channel: %r", chan)
        chan.validate()
        idx = chan.number

        mv = memoryview(self.mem)

        start = idx * 16
        cflags_start = idx * 2 + 0x5F80

        chan.to_data(
            mv[start : start + 16], mv[cflags_start : cflags_start + 2]
        )

    def find_first_hidden_channel(self, start: int = 0) -> Channel | None:
        for idx in range(start, consts.NUM_CHANNELS):
            chan = self.get_channel(idx)
            if chan.hide_channel:
                return chan

        return None

    def get_autowrite_channels(self) -> ty.Iterable[Channel]:
        # load position map
        mv = memoryview(self.mem)

        chan_pos = [255] * consts.NUM_AUTOWRITE_CHANNELS
        chan_positiions = mv[0x6A30:]
        for idx in range(consts.NUM_AUTOWRITE_CHANNELS):
            if (pos := chan_positiions[idx]) < consts.NUM_AUTOWRITE_CHANNELS:
                chan_pos[pos] = idx

        # load only channels that are in pos map
        for idx in range(consts.NUM_AUTOWRITE_CHANNELS):
            if (cpos := chan_pos[idx]) != 255:
                start = idx * 16 + 0x5140
                data = mv[start : start + 16]
                chan = Channel.from_data(cpos, data, None)
                yield chan

    def get_scan_edge(self, idx: int) -> ScanEdge:
        if idx < 0 or idx > consts.NUM_SCAN_EDGES - 1:
            raise IndexError

        start = 0x5DC0 + idx * 16
        return ScanEdge.from_data(idx, self.mem[start : start + 16])

    def set_scan_edge(self, se: ScanEdge) -> None:
        se.validate()
        start = 0x5DC0 + se.idx * 16
        mv = memoryview(self.mem)
        se.to_data(mv[start : start + 16])

    def get_active_channels(self) -> ty.Iterable[Channel]:
        for cidx in range(consts.NUM_CHANNELS):
            chan = self.get_channel(cidx)
            if not chan.hide_channel and chan.freq:
                yield chan

    def _get_channel_flags(self, idx: int) -> ChannelFlags:
        if idx < 0 or idx > consts.NUM_CHANNELS - 1:
            raise IndexError

        cflags_start = idx * 2 + 0x5F80
        return ChannelFlags.from_data(
            idx,
            self.mem[cflags_start : cflags_start + 2],
        )

    def _get_channels_in_bank(self, bank: int) -> ty.Iterable[ChannelFlags]:
        mv = memoryview(self.mem)
        mem_flags = mv[0x5F80:]
        for channum in range(consts.NUM_CHANNELS):
            start = channum * 2
            cf = ChannelFlags.from_data(channum, mem_flags[start : start + 2])
            if cf.bank == bank and not cf.hide_channel:
                yield cf

    def get_bank(self, idx: int) -> Bank:
        _LOG.debug("loading bank %d", idx)
        if idx < 0 or idx > consts.NUM_BANKS - 1:
            raise IndexError

        start = 0x6D10 + idx * 8
        return Bank.from_data(idx, self.mem[start : start + 8])

    def get_bank_channels(self, bank_idx: int) -> BankChannels:
        _LOG.debug("loading bank channels %d", bank_idx)
        if bank_idx < 0 or bank_idx > consts.NUM_BANKS - 1:
            raise IndexError

        # TODO: confilicts / doubles
        bc = BankChannels()
        bc.set(self._get_channels_in_bank(bank_idx))
        return bc

    def set_bank(self, bank: Bank) -> None:
        idx = bank.idx
        mv = memoryview(self.mem)
        start = 0x6D10 + idx * 8
        bank.to_data(mv[start : start + 8])

    def get_scan_link(self, idx: int) -> ScanLink:
        if idx < 0 or idx > consts.NUM_SCAN_LINKS - 1:
            raise IndexError

        start = 0x6DC0 + idx * 8
        # edges
        estart = 0x6C2C + 4 * idx

        return ScanLink.from_data(
            idx, self.mem[start : start + 8], self.mem[estart : estart + 4]
        )

    def set_scan_link(self, sl: ScanLink) -> None:
        mv = memoryview(self.mem)
        start = 0x6DC0 + sl.idx * 8
        # edges mapping
        estart = 0x6C2C + 4 * sl.idx
        sl.to_data(mv[start : start + 8], mv[estart : estart + 4])

    def get_settings(self) -> RadioSettings:
        return RadioSettings.from_data(self.mem[0x6BD0 : 0x6BD0 + 64])

    def set_settings(self, sett: RadioSettings) -> None:
        mv = memoryview(self.mem)
        sett.to_data(mv[0x6BD0 : 0x6BD0 + 64])

    def get_bank_links(self) -> BankLinks:
        return BankLinks.from_data(self.mem[0x6C28 : 0x6C28 + 3])

    def set_bank_links(self, bl: BankLinks) -> None:
        mv = memoryview(self.mem)
        bl.to_data(mv[0x6C28 : 0x6C28 + 3])

    def get_comment(self) -> str:
        cmt = self.mem[0x6D00 : 0x6D00 + 16]
        return cmt.decode().rstrip()

    def set_comment(self, comment: str) -> None:
        cmt = fix_comment(comment).ljust(16).encode()
        mv = memoryview(self.mem)
        mv[0x6D00 : 0x6D00 + 16] = cmt

    def is_usa_model(self) -> bool:
        return self.file_etcdata == "0003"


def decode_name(inp: abc.Sequence[int]) -> str:
    """Decode name from 5-bytes that contains 6 - 6bits coded characters with
    4-bit padding on beginning..

          76543210
       0  xxxx0000
       1  00111111
       2  22222233
       3  33334444
       4  44555555
    """
    if len(inp) != consts.ENCODED_NAME_LEN:
        raise ValueError

    chars = (
        (inp[0] & 0b00001111) << 2 | (inp[1] & 0b11000000) >> 6,
        (inp[1] & 0b00111111),
        (inp[2] & 0b11111100) >> 2,
        (inp[2] & 0b00000011) << 4 | (inp[3] & 0b11110000) >> 4,
        (inp[3] & 0b00001111) << 2 | (inp[4] & 0b11000000) >> 6,
        (inp[4] & 0b00111111),
    )

    name = "".join(consts.CODED_CHRS[x] for x in chars)
    if name and name[0] == "^":
        # invalid name
        return ""

    return name.rstrip()


def encode_name(inp: str) -> abc.Sequence[int]:
    inp = inp[: consts.NAME_LEN].upper().ljust(consts.NAME_LEN)

    iic = [0 if x == "^" else consts.CODED_CHRS.index(x) for x in inp]
    return [
        (iic[0] & 0b00111100) >> 2,  # padding
        ((iic[0] & 0b00000011) << 6) | (iic[1] & 0b00111111),
        ((iic[2] & 0b00111111) << 2) | ((iic[3] & 0b00110000) >> 4),
        ((iic[3] & 0b00001111) << 4) | ((iic[4] & 0b00111100) >> 2),
        ((iic[4] & 0b00000011) << 6) | (iic[5] & 0b00111111),
    ]


def decode_freq(freq: int, flags: int) -> int:
    """
    flags are probably only 2 bits:
        00 -> 5000
        01 -> 6250
        10 -> 8333.3333
        11 -> 9000
    """
    # TODO: check:
    match flags:
        case 0b00:
            return 5000 * freq
        case 0b01:
            return 6250 * freq
        case 0b10:
            return (25000 * freq) // 3  # unused?
        case 0b11:
            return 9000 * freq

    _LOG.error("unknown flag %r for freq %r", flags, freq)
    raise ValueError


class EncodedFreq(ty.NamedTuple):
    flags: int
    freq: int
    offset: int

    def freq_bytes(self) -> tuple[int, int, int]:
        # freq0, freq1, freq2
        return (
            self.freq & 0x00FF,
            (self.freq & 0xFF00) >> 8,
            (self.freq & 0x30000) >> 16,
        )

    def offset_bytes(self) -> tuple[int, int]:
        # offset_l, offset_h
        return self.offset & 0x00FF, (self.offset & 0xFF00) >> 8


class InvalidFlagError(ValueError):
    pass


def encode_freq(freq: int, offset: int) -> EncodedFreq:
    # freq min 0.1MHz
    # offset max 159.995 MHz
    # flag is <offset_flag:2b><freq_flag:2b>
    flags = 0
    if freq % 5000 == freq % 9000 == 0:
        flags = 0b0 if offset else 0b1111  # 9k step or 50 step
    elif freq % 9000 == 0:
        flags = 0b1111
    elif freq % 5000 == 0:
        flags = 0
    elif freq % 6250 == 0:
        flags = 0b0101
    elif (freq * 3) % 25000 == 0:  # not used?
        flags = 0b1010
    else:
        raise InvalidFlagError

    match flags & 0b11:
        case 0b11:  # 9k
            return EncodedFreq(flags, freq // 9000, offset // 9000)
        case 0b10:  # 8333.333
            return EncodedFreq(
                flags, (freq * 3) // 25000, (offset * 3) // 25000
            )
        case 0b01:  # 6250
            return EncodedFreq(flags, freq // 6250, offset // 6250)
        case 0b00:  # 5k
            return EncodedFreq(flags, freq // 5000, offset // 5000)

    raise ValueError


def validate_frequency(inp: str | int) -> bool:
    if isinstance(inp, str):
        try:
            freq = int(inp)
        except ValueError:
            return False
    else:
        freq = inp

    if freq > consts.MAX_FREQUENCY or freq < 0:
        return False

    try:
        encode_freq(freq, 0)
    except ValueError:
        return False

    return True


def validate_offset(inp: str | int) -> bool:
    if isinstance(inp, str):
        try:
            freq = int(inp)
        except ValueError:
            return False
    else:
        freq = inp

    if freq > consts.MAX_OFFSET or freq < 0:
        return False

    try:
        encode_freq(freq, freq)
    except ValueError:
        return False

    return True


def validate_name(name: str) -> None:
    if len(name) > 6:
        raise ValueError

    if any(i not in consts.VALID_CHAR for i in name.upper()):
        raise ValueError


def validate_comment(comment: str) -> None:
    if len(comment) > 16:
        raise ValueError

    if any(i not in consts.VALID_CHAR for i in comment.upper()):
        raise ValueError


def fix_frequency(freq: int) -> int:
    freq = max(freq, consts.MIN_FREQUENCY)
    freq = min(freq, consts.MAX_FREQUENCY)

    div = (5000, 9000, 6250, 8333.333)
    nfreqs = (int((freq // f) * f) for f in div)
    err_freq = ((freq - nf, nf) for nf in nfreqs)
    _, nfreq = min(err_freq)
    return nfreq


def default_mode_for_freq(freq: int) -> int:
    if freq > 144_000_000:
        return 0  # FM

    if freq > 108_000_000:  # air-band
        return 0  # AM

    if freq > 68_000_000:  # fm radio
        return 1  # WFM

    if freq > 30_000_000:
        return 0  # FM

    return 2  # AM


def fix_name(name: str) -> str:
    name = name.rstrip().upper()
    if not name:
        return ""

    name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "replace").decode()
    )
    name = "".join(c for c in name if c in consts.VALID_CHAR)
    return name[:6]


def fix_comment(name: str) -> str:
    name = name.rstrip()
    if not name:
        return ""

    name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "replace").decode()
    )
    name = "".join(c for c in name if c.upper() in consts.VALID_CHAR)
    return name[:16]


def tuning_steps_for_freq(freq: int) -> list[str]:
    """From manual: additional steps become selectable in only the
    VHF Air band (8.33 kHz) and in the AM broadcast band (9 kHz).
    """

    if freq < 1_620_000:
        return consts.AVAIL_STEPS_BROADCAST

    if 118_000_000 <= freq <= 135_995_000:
        return consts.AVAIL_STEPS_AIR

    return consts.AVAIL_STEPS_NORMAL

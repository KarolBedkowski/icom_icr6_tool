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

from . import coding, consts

_LOG = logging.getLogger(__name__)
DEBUG = True

MutableMemory = abc.MutableSequence[int] | memoryview


@dataclass
class RadioModel:
    # Data format - 40B
    # model: 4B
    # unknown: 1B - is this mapped to region?
    #        TODO: check
    #        0-0xc -> 1; 0xd-0x22 -> 2; 0x23 -> 3; 0x2e -> 5; other -> error
    #        1,2,5 = > us; 3 -> global (??)
    # rev: 1B
    # comment: 16B
    # unknown: 3B
    # serial 14B
    #    4b
    #    1B unknown
    #    2b
    #    7b unknown
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
                "unk3": data[29],
                "unk4": data[32:],
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


class ValidateError(ValueError):
    def __init__(self, field: str, value: object) -> None:
        self.field = field
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
    def not_hidden(self) -> bool:
        return not self.hide_channel and self.freq > 0

    def __str__(self) -> str:
        try:
            bank = f"{consts.BANK_NAMES[self.bank]}/{self.bank_pos}"
        except IndexError:
            bank = f"{self.bank}/{self.bank_pos}"

        return (
            f"Channel {self.number}: "
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
                    data[4] & 0b11000000,
                    data[4] & 0b00001000,  # TODO: flag "is channel valid"?
                    data[7] & 0b11000000,
                    data[10] & 0b01111000,
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
            bank = cflags[0] & 0b00011111  # TODO: verify
            bank_pos = cflags[1]  # TODO: verify
        else:
            hide_channel = skip = bank = bank_pos = 0

        duplex = d if (d := (data[4] & 0b00110000) >> 4) <= 2 else 0
        tone_mode = t if (t := data[4] & 0b00000111) <= 4 else 0
        tsql_freq = (
            ts if (ts := data[7] & 0b00111111) < len(consts.CTCSS_TONES) else 0
        )
        dtsc = d if (d := data[8] & 0b01111111) < len(consts.DTCS_CODES) else 0
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
            dtsc=dtsc,
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
        print(repr(enc_freq), bin(data[2]))
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
        # polarity, dtsc
        data[8] = bool2bit(self.polarity, 0b10000000) | (
            self.dtsc & 0b01111111
        )
        # canceller freq
        canc_freq = self.canceller_freq // 10
        data[9] = (canc_freq & 0b111111110) >> 1
        data_set(data, 10, 0b10000000, (canc_freq & 1) << 7)
        # vsc & cancelelr
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
        if not validate_frequency(self.freq):
            raise ValidateError("freq", self.freq)

        _is_valid_index(consts.MODES, self.mode, "mode")
        _is_valid_index(consts.STEPS, self.tuning_step, "tuning step")
        _is_valid_index(consts.SKIPS, self.skip, "skip")

        _is_valid_index(consts.DUPLEX_DIRS, self.duplex, "duplex")
        if not validate_offset(self.freq, self.offset):
            raise ValidateError("offset", self.offset)

        _is_valid_index(consts.TONE_MODES, self.tone_mode, "tone mode")
        # TSQL
        _is_valid_index(consts.CTCSS_TONES, self.tsql_freq, "tsql freq")
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
            "af": self.af_filter,
            "att": self.attenuator,
            "mode": consts.MODES[self.mode],
            "ts": consts.STEPS[self.tuning_step],
            "dup": consts.DUPLEX_DIRS[self.duplex],
            "tone_mode": consts.TONE_MODES[self.tone_mode],
            "offset": self.offset,
            "tsql_freq": _try_get(consts.CTCSS_TONES, self.tsql_freq),
            "dtsc": _try_get(consts.DTCS_CODES, self.dtsc),
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
        # TODO: adjust freq
        _LOG.debug("from_record: %r", data)
        if (freq := data.get("freq")) is not None:
            ifreq = int(freq or "0")  # type: ignore
            self.freq = fix_frequency(ifreq) if ifreq else 0

            # TODO: ?
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
            self.offset = fix_offset(self.freq, off) if off else 0

        if (tf := data.get("tsql_freq")) is not None:
            self.tsql_freq = get_index_or_default(consts.CTCSS_TONES, tf)

        if (dtsc := data.get("dtsc")) is not None:
            self.dtsc = get_index_or_default(consts.DTCS_CODES, dtsc)

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
            self.name = fix_name(str(n))

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
        self.tuning_step = 0  # TODO: default
        self.duplex = 0
        self.offset = 0
        self.tone_mode = 0
        self.tsql_freq = 0
        self.dtsc = 0
        self.polarity = 0
        self.vsc = False
        self.skip = 0


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

    debug_info: dict[str, object] | None = None

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
        edata[3] = (edges >> 24) & 0xFF

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
    # TODO: check - always False
    disabled: int
    mode: int
    # tuning_step include 15 - "-"
    tuning_step: int
    attenuator: int
    name: str

    debug_info: dict[str, object] | None = None

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
        cls: type[ScanEdge], idx: int, data: bytearray | memoryview
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
            debug_info={"raw": binascii.hexlify(data)} if DEBUG else None,
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
            validate_name(self.name)
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

    @classmethod
    def from_data(
        cls: type[RadioSettings], data: bytearray | memoryview
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
            debug_info={"raw": binascii.hexlify(data)} if DEBUG else None,
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
        # 001A = EU, 0003 = USA, 002A - ?
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
        if not chan.freq or chan.hide_channel:
            chan.bank = consts.BANK_NOT_SET

        chan.validate()
        idx = chan.number

        mv = memoryview(self.mem)

        start = idx * 16
        cflags_start = idx * 2 + 0x5F80

        chan.to_data(
            mv[start : start + 16], mv[cflags_start : cflags_start + 2]
        )

        # remove other channels from this position
        if chan.bank != consts.BANK_NOT_SET:
            for cf in self._get_channels_in_bank(chan.bank):
                if cf.channum != chan.number and cf.bank_pos == chan.bank_pos:
                    cf.bank = consts.BANK_NOT_SET
                    self._set_channel_flags(cf)

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
        _LOG.debug("set_scan_edge: %r", se)
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

    def _set_channel_flags(self, cf: ChannelFlags) -> None:
        if cf.hide_channel:
            cf.bank = consts.BANK_NOT_SET

        cflags_start = cf.channum * 2 + 0x5F80
        mv = memoryview(self.mem)
        mem_flags = mv[cflags_start : cflags_start + 2]
        cf.to_data(mem_flags)

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

    def clear_bank_pos(self, bank: int, bank_pos: int) -> bool:
        _LOG.debug("clear_bank_pos: %d, %d", bank, bank_pos)
        bc = self.get_bank_channels(bank)
        channum = bc[bank_pos]
        if channum is None:
            _LOG.debug("clear_bank_pos: no chan in pos %d", bank_pos)
            return False

        _LOG.debug("clear_bank_pos: chan %d in pos %d", channum, bank_pos)
        cf = self._get_channel_flags(channum)
        cf.bank = consts.BANK_NOT_SET
        cf.bank_pos = 0
        self._set_channel_flags(cf)

        return True

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
        return self.mem[0x6D00 : 0x6D00 + 16].decode().rstrip()

    def set_comment(self, comment: str) -> None:
        cmt = fix_comment(comment).ljust(16).encode()
        mv = memoryview(self.mem)
        mv[0x6D00 : 0x6D00 + 16] = cmt

    def is_usa_model(self) -> bool:
        return self.file_etcdata == "0003"

    def remap_scan_links(self, mapping: dict[int, int]) -> None:
        for i in range(consts.NUM_SCAN_LINKS):
            sl = self.get_scan_link(i)
            sl.remap_edges(mapping)
            self.set_scan_link(sl)


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
        coding.encode_freq(freq, 0)
    except ValueError:
        return False

    return True


def validate_offset(freq: int, inp: str | int) -> bool:
    if isinstance(inp, str):
        try:
            offset = int(inp)
        except ValueError:
            return False
    else:
        offset = inp

    if offset == 0:
        return True

    if offset > consts.MAX_OFFSET or offset < consts.MIN_OFFSET:
        return False

    try:
        coding.encode_freq(freq, offset)
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


def _first_min_diff(base: float, values: ty.Iterable[int]) -> float:
    minimal = base
    err = 99999999999.0
    # keep order; using min not always return first minimal value
    for v in values:
        if (nerr := abs(base - v)) < err:
            err = nerr
            minimal = v

    return minimal


def _fix_frequency(freq: int, base_freq: int) -> int:
    """base_freq is channel frequency;
    freq is channel freq or offset to correct
    """
    # try exact match
    if not freq % 5000 or not freq % 6250:
        return freq

    if 495_000 <= base_freq <= 1_620_000 and not freq % 9000:
        return freq

    if consts.is_air_band(base_freq):
        # TODO: check which work better
        if round(freq * 3 / 25000.0) == freq:
            return freq

        if not freq % 8333 or freq % 10 in (3, 6):
            return freq

    # try find best freq
    nfreqs = [
        (freq // 5000) * 5000,
        (freq // 5000 + 1) * 5000,
        (freq // 6250) * 6250,
        (freq // 6250 + 1) * 6250,
    ]

    # TODO: 9k is not used for rounding?
    # if 495_000 <= freq <= 1_620_000:
    #    nfreqs.append(round(freq / 9000) * 9000)

    if consts.is_air_band(base_freq):
        # nfreqs.append((round(freq * 3 / 25000.0) * 25000) // 3)
        nfreqs.extend(
            (
                ((freq * 3 // 25000) * 25000) // 3,
                ((freq * 3 // 25000 + 1) * 25000) // 3,
            )
        )

    return int(_first_min_diff(freq, nfreqs))


def fix_frequency(freq: int, *, usa_model: bool = False) -> int:
    freq = max(freq, consts.MIN_FREQUENCY)
    freq = min(freq, consts.MAX_FREQUENCY)

    if usa_model:
        # if freq is forbidden range; set freq to nearest valid freq.
        for fmin, fmax in consts.USA_FREQ_UNAVAIL_RANGES:
            if fmin < freq < fmax:
                freq = fmin if (freq - fmin) < (fmax - freq) else fmax
                break

    return _fix_frequency(freq, freq)


def fix_offset(freq: int, offset: int) -> int:
    if offset == 0:
        return 0

    offset = max(offset, 5000)
    offset = min(offset, 159995000)

    if offset % 9000 == 0:
        # 9k is used only if match exactly
        return offset

    return _fix_frequency(offset, freq)


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

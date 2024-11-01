# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
# ruff: noqa: PLR2004
""" """

from __future__ import annotations

import binascii
import logging
import typing as ty
import unicodedata
from dataclasses import dataclass

from . import consts

_LOG = logging.getLogger(__name__)


@dataclass
class RadioModel:
    rev: int
    comment: bytes


def _try_get(inlist: list[str] | tuple[str, ...], idx: int) -> str:
    try:
        return inlist[idx]
    except IndexError:
        return f"<[{idx}]>"


def bool2bit(val: bool | int, mask: int) -> int:
    return mask if val else 0


def set_bits(value: int, newval: int, mask: int) -> int:
    return (value & (~mask)) | (newval & mask)


def set_bit(value: int, newval: object, bit: int) -> int:
    mask = 1 << bit
    if newval:
        return value | mask

    return value & (~mask)


def data_set_bit(
    data: list[int], offset: int, bit: int, value: object
) -> None:
    if value:
        data[offset] = data[offset] | (1 << bit)
    else:
        data[offset] = data[offset] & (~(1 << bit))


def data_set(data: list[int], offset: int, mask: int, value: int) -> None:
    data[offset] = (data[offset] & (~mask)) | (value & mask)


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
    tmode: int
    # tsql freq
    ctone: int
    # dtsc code
    dtsc: int
    # dtsc polarity
    polarity: int
    vsc: bool

    canceller: int
    canceller_freq: int

    unknowns: list[int]

    # control flags
    hide_channel: bool
    skip: int
    # 31 = no bank
    bank: int
    bank_pos: int

    raw: bytes
    raw_freqs: tuple[int, int, int]

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
            f"ts={self.tuning_step}, "
            f"duplex={consts.DUPLEX_DIRS[self.duplex]}, "
            f"tmode={consts.TONE_MODES[self.tmode]}, "
            f"offset={self.offset}, "
            f"ctone={_try_get(consts.CTCSS_TONES, self.ctone)}, "
            f"dtsc={_try_get(consts.DTCS_CODES, self.dtsc)}, "
            f"cf={self.canceller_freq}, "
            f"vsc={self.vsc}, "
            f"c={self.canceller}, "
            f"name={self.name!r}, "
            f"hide={self.hide_channel}, "
            f"skip={consts.SKIPS[self.skip]}, "
            f"polarity={consts.POLARITY[self.polarity]}, "
            f"bank={bank}, "
            f"unknowns={self.unknowns}, "
            f"raws={binascii.hexlify(self.raw)!r}, "
            f"raw_freqs={self.raw_freqs}, "
        )

    def __lt__(self, other: object) -> bool:
        assert isinstance(other, Channel)
        return self.number < other.number

    @classmethod
    def from_data(
        cls: type[Channel],
        idx: int,
        data: bytes | list[int],
        cflags: bytes | list[int] | None,
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

        unknowns = [
            data[4] & 0b11000000,
            data[4] & 0b00001000,  # TODO: flag "is channel valid"?
            data[7] & 0b11111110,
            data[10] & 0b01111000,
        ]

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
            tmode=data[4] & 0b00000111,
            offset=offset_real,
            ctone=data[7] & 0b00111111,
            polarity=(data[8] & 0b10000000) >> 7,
            dtsc=(data[8] & 0b01111111),
            canceller_freq=(data[9] << 1) | ((data[10] & 0b10000000) >> 7),
            vsc=bool(data[10] & 0b00000100),
            canceller=bool(data[10] & 0b00000011),
            name=decode_name(data[11:16]),
            hide_channel=bool(hide_channel),
            skip=skip,
            bank=bank,
            bank_pos=bank_pos,
            unknowns=unknowns,
            raw=bytes(data),
            raw_freqs=(freq, offset, (data[2] & 0b11110000) >> 4),
        )

    def to_data(self, data: list[int], cflags: list[int]) -> None:
        enc_freq = encode_freq(self.freq, self.offset)
        freq0, freq1, freq2 = enc_freq.freq_bytes()
        offset_l, offset_h = enc_freq.offset_bytes()

        # freq
        data[0] = freq0
        data[1] = freq1
        # flags & freq2
        print(repr(enc_freq), bin(data[2]))
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
        # tmode
        data_set(data, 4, 0b00000111, self.tmode)
        # offset
        data[5] = offset_l
        data[6] = offset_h
        # ctone
        data_set(data, 7, 0b00111111, self.ctone)
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
        data[11:16] = encode_name(self.name)

        # hide_channel, bank
        cflags[0] = (
            bool2bit(self.hide_channel, 0b10000000)
            | ((self.skip & 0b11) << 5)
            | (self.bank & 0b00011111)
        )
        # bank_pos
        cflags[1] = self.bank_pos


@dataclass
class Bank:
    idx: int
    # 6 characters
    name: str
    # list of channels in bank; update via channel
    channels: list[int | None]

    def find_free_slot(self, start: int = 0) -> int | None:
        for idx in range(start, len(self.channels)):
            if self.channels[idx] is None:
                return idx

        return None

    @classmethod
    def from_data(cls: type[Bank], idx: int, data: bytes | list[int]) -> Bank:
        return Bank(
            idx,
            name=bytes(data[0:6]).decode() if data[0] else "",
            channels=[None] * 100,
        )

    def to_data(self, data: list[int]) -> None:
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
        cls: type[ScanLink], idx: int, data: list[int], edata: list[int]
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

    def to_data(self, data: list[int], edata: list[int]) -> None:
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
    ts: int
    attn: int
    name: str

    def human_attn(self) -> str:
        match self.attn:
            case 0:
                return "Off"
            case 1:
                return "On"
            case 2:
                return "-"

        return str(self.attn)

    def delete(self) -> None:
        self.start = self.end = 0
        self.disabled = True

    @classmethod
    def from_data(cls: type[ScanEdge], idx: int, data: list[int]) -> ScanEdge:
        start = (data[3] << 24) | (data[2] << 16) | (data[1] << 8) | data[0]
        start *= 3
        end = (data[7] << 24) | (data[6] << 16) | (data[5] << 8) | data[4]
        end *= 3

        return ScanEdge(
            idx=idx,
            start=start,
            end=end,
            disabled=bool(data[8] & 0b10000000),
            mode=(data[8] & 0b01110000) >> 4,
            ts=(data[8] & 0b00001111),
            attn=(data[9] & 0b00110000) >> 4,
            name=bytes(data[10:16]).decode() if data[10] else "",
        )

    def to_data(self, data: list[int]) -> None:
        start = self.start // 3
        data[0] = start & 0xFF
        data[1] = (start >> 8) & 0xFF
        data[2] = (start >> 16) & 0xFF
        data[3] = (start >> 24) & 0xFF

        end = self.end // 3
        data[4] = end & 0xFF
        data[5] = (end >> 8) & 0xFF
        data[6] = (end >> 16) & 0xFF
        data[7] = (end >> 24) & 0xFF

        data[8] = (
            bool2bit(self.disabled, 0b10000000)
            | (self.mode & 0b111) << 4
            | (self.ts & 0b1111)
        )

        data_set(data, 9, 0b00110000, self.attn << 4)

        if self.name:
            data[10:16] = self.name[:6].ljust(6).encode()
        else:
            data[10:16] = [0, 0, 0, 0, 0, 0]


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
        cls: type[RadioSettings], data: bytes | list[int]
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

    def to_data(self, data: list[int]) -> None:
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
    def from_data(cls: type[BankLinks], data: bytes | list[int]) -> BankLinks:
        # Y -> A
        assert len(data) == 3
        banks = ((data[2] & 0b00111111) << 16) | (data[1] << 8) | data[0]
        return BankLinks(banks)

    def to_data(self, data: list[int]) -> None:
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
        self.mem = [0] * consts.MEM_SIZE
        self._cache_channels: dict[int, Channel] = {}
        self._cache_banks: dict[int, Bank] = {}

    def reset(self) -> None:
        self._cache_banks.clear()
        self._cache_channels.clear()

    def update_from(self, rm: RadioMemory) -> None:
        self.mem = rm.mem
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

    def get_channel(self, idx: int) -> Channel:
        if idx < 0 or idx > consts.NUM_CHANNELS - 1:
            raise IndexError

        if chan := self._cache_channels.get(idx):
            return chan

        start = idx * 16
        data = self.mem[start : start + 16]

        cflags_start = idx * 2 + 0x5F80
        cflags = self.mem[cflags_start : cflags_start + 2]

        chan = Channel.from_data(idx, data, cflags)
        self._cache_channels[idx] = chan

        return chan

    def set_channel(self, chan: Channel) -> None:
        _LOG.debug("set_channel: %r", chan)
        idx = chan.number

        self._cache_channels[idx] = chan
        self._cache_banks.clear()

        start = idx * 16
        data = self.mem[start : start + 16]

        cflags_start = idx * 2 + 0x5F80
        cflags = self.mem[cflags_start : cflags_start + 2]

        chan.to_data(data, cflags)
        self.mem[start : start + 16] = data
        self.mem[cflags_start : cflags_start + 2] = cflags

    def get_autowrite_channels(self) -> ty.Iterable[Channel]:
        for idx in range(consts.NUM_AUTOWRITE_CHANNELS):
            start = idx * 16 + 0x5140
            data = self.mem[start : start + 16]
            chan = Channel.from_data(idx, data, None)

            # chan pos
            # TODO: CHECK !!!!
            if (pos := self.mem[idx + 0x6A30]) < consts.NUM_AUTOWRITE_CHANNELS:
                chan.number = pos
                yield chan

    def get_scan_edge(self, idx: int) -> ScanEdge:
        if idx < 0 or idx > consts.NUM_SCAN_EDGES - 1:
            raise IndexError

        start = 0x5DC0 + idx * 16
        data = self.mem[start : start + 16]

        return ScanEdge.from_data(idx, data)

    def set_scan_edge(self, se: ScanEdge) -> None:
        idx = se.idx
        start = 0x5DC0 + idx * 16
        data = self.mem[start : start + 16]

        se.to_data(data)

        self.mem[start : start + 16] = data

    def _get_active_channels(self) -> ty.Iterable[Channel]:
        for cidx in range(consts.NUM_CHANNELS):
            chan = self.get_channel(cidx)
            if not chan.hide_channel and chan.freq:
                yield chan

    def get_bank(self, idx: int) -> Bank:
        if idx < 0 or idx > consts.NUM_BANKS - 1:
            raise IndexError

        if bank := self._cache_banks.get(idx):
            return bank

        start = 0x6D10 + idx * 8
        data = self.mem[start : start + 8]

        bank = Bank.from_data(idx, data)

        # TODO: confilicts / doubles
        for chan in self._get_active_channels():
            if chan.bank == idx:
                bank.channels[chan.bank_pos] = chan.number

        self._cache_banks[idx] = bank
        return bank

    def set_bank(self, bank: Bank) -> None:
        idx = bank.idx
        self._cache_banks[idx] = bank

        start = 0x6D10 + idx * 8
        data = self.mem[start : start + 8]

        bank.to_data(data)

        self.mem[start : start + 8] = data

    def get_scan_link(self, idx: int) -> ScanLink:
        if idx < 0 or idx > consts.NUM_SCAN_LINKS - 1:
            raise IndexError

        start = 0x6DC0 + idx * 8
        data = self.mem[start : start + 8]

        # edges
        estart = 0x6C2C + 4 * idx
        edata = self.mem[estart : estart + 4]

        return ScanLink.from_data(idx, data, edata)

    def set_scan_link(self, sl: ScanLink) -> None:
        start = 0x6DC0 + sl.idx * 8
        data = self.mem[start : start + 8]

        # edges mapping
        estart = 0x6C2C + 4 * sl.idx
        edata = self.mem[estart : estart + 4]

        sl.to_data(data, edata)

        self.mem[start : start + 8] = data
        self.mem[estart : estart + 4] = edata

    def get_settings(self) -> RadioSettings:
        data = self.mem[0x6BD0 : 0x6BD0 + 64]
        return RadioSettings.from_data(data)

    def set_settings(self, sett: RadioSettings) -> None:
        data = self.mem[0x6BD0 : 0x6BD0 + 64]
        sett.to_data(data)
        self.mem[0x6BD0 : 0x6BD0 + 64] = data

    def get_bank_links(self) -> BankLinks:
        data = self.mem[0x6C28 : 0x6C28 + 3]
        return BankLinks.from_data(data)

    def set_bank_links(self, bl: BankLinks) -> None:
        data = self.mem[0x6C28 : 0x6C28 + 3]
        bl.to_data(data)
        self.mem[0x6C28 : 0x6C28 + 3] = data



def decode_name(inp: list[int] | bytes) -> str:
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

    return "".join(consts.CODED_CHRS[x] for x in chars)


def encode_name(inp: str) -> list[int]:
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

    if consts.MAX_FREQUENCY < freq < 0:
        return False

    try:
        encode_freq(freq, 0)
    except ValueError:
        return False

    return True


def validate_name(name: str) -> None:
    if len(name) > 6:
        raise ValueError

    if any(i not in consts.VALID_CHAR for i in name.upper()):
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

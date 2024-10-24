# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import binascii
import logging
import typing as ty
from dataclasses import dataclass

LOG = logging.getLogger(__name__)


@dataclass
class RadioModel:
    rev: int
    comment: bytes


NUM_CHANNELS: ty.Final[int] = 1300
NUM_BANKS: ty.Final[int] = 22
NUM_SCAN_EDGES: ty.Final[int] = 25
NUM_SCAN_LINKS: ty.Final[int] = 10
NAME_LEN: ty.Final[int] = 6

MAX_FREQUENCY: ty.Final[int] = 1309995000

TONE_MODES = ["", "TSQL", "TSQL-R", "DTCS", "DTCS-R", "", "", ""]
DUPLEX_DIRS = ["", "-", "+", ""]
MODES = ["FM", "WFM", "AM", "Auto", "-"]
STEPS = [
    "5",
    "6.25",
    "8.333333",
    "9",
    "10",
    "12.5",
    "15",
    "20",
    "25",
    "30",
    "50",
    "100",
    "125",
    "200",
    "Auto",
    "",
]
SKIPS = ["", "S", "", "P"]
# 31 = not set
BANK_NAMES = "ABCDEFGHIJKLMNOPQRTUWY"
BANK_NOT_SET = 31
POLARITY = ["Reverse", "Normal"]

# https://pl.wikipedia.org/wiki/CTCSS
CTCSS_TONES = (
    "67,0 ",
    "69,3",
    "71,9",
    "74,4",
    "77,0",
    "79,7",
    "82,5",
    "85,4",
    "88,5",
    "91,5",
    "94,8",
    "97,4",
    "100,03",
    "103,54",
    "107,25",
    "110,96",
    "114,87",
    "118,88",
    "123,09",
    "127,30",
    "131,81",
    "136,52",
    "141,33",
    "146,24",
    "151,45",
    "156,76",
    "159,87",
    "162,28",
    "165,59",
    "167,90",
    "171,31",
    "173,82",
    "177,33",
    "179,94",
    "183,55",
    "186,26",
    "189,97",
    "192,88",
    "196,69",
    "199,50",
    "203,51",
    "206,52",
    "210,73",
    "218,14",
    "225,75",
    "229,16",
    "233,67",
    "241,88",
    "250,39",
    "254,10",
    "",
)

DTCS_CODES = [
    "023",
    "025",
    "026",
    "031",
    "032",
    "043",
    "047",
    "051",
    "053",
    "054",
    "065",
    "071",
    "072",
    "073",
    "074",
    "114",
    "115",
    "116",
    "122",
    "125",
    "131",
    "132",
    "134",
    "143",
    "152",
    "155",
    "156",
    "162",
    "165",
    "172",
    "174",
    "205",
    "212",
    "223",
    "225",
    "226",
    "243",
    "244",
    "245",
    "246",
    "251",
    "252",
    "261",
    "263",
    "265",
    "266",
    "271",
    "306",
    "311",
    "315",
    "325",
    "331",
    "343",
    "346",
    "351",
    "364",
    "365",
    "371",
    "411",
    "412",
    "413",
    "423",
    "425",
    "431",
    "432",
    "445",
    "446",
    "452",
    "455",
    "464",
    "465",
    "466",
    "503",
    "506",
    "516",
    "521",
    "525",
    "532",
    "546",
    "552",
    "564",
    "565",
    "606",
    "612",
    "624",
    "627",
    "631",
    "632",
    "645",
    "652",
    "654",
    "662",
    "664",
    "703",
    "712",
    "723",
    "725",
    "726",
    "731",
    "732",
    "734",
    "743",
    "754",
    "",
]


def _try_get(inlist: list[str] | tuple[str, ...], idx: int) -> str:
    try:
        return inlist[idx]
    except IndexError:
        return f"<[{idx}]>"


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

    def delete(self) -> None:
        self.freq = 0
        self.hide_channel = True

    def clear_bank(self) -> None:
        self.bank = BANK_NOT_SET
        self.bank_pos = 0

    def __str__(self) -> str:
        ic(self)
        try:
            bank = f"{BANK_NAMES[self.bank]}/{self.bank_pos}"
        except IndexError:
            bank = f"{self.bank}/{self.bank_pos}"

        return (
            "Channel {self.number}: "
            f"f={self.freq}, "
            f"ff={self.freq_flags}, "
            f"af={self.af_filter}, "
            f"att={self.attenuator}, "
            f"mode={MODES[self.mode]}, "
            f"ts={self.tuning_step}, "
            f"duplex={DUPLEX_DIRS[self.duplex]}, "
            f"tmode={TONE_MODES[self.tmode]}, "
            f"offset={self.offset}, "
            f"ctone={_try_get(CTCSS_TONES, self.ctone)}, "
            f"dtsc={_try_get(DTCS_CODES, self.dtsc)}, "
            f"cf={self.canceller_freq}, "
            f"vsc={self.vsc}, "
            f"c={self.canceller}, "
            f"name={self.name!r}, "
            f"hide={self.hide_channel}, "
            f"skip={SKIPS[self.skip]}, "
            f"polarity={POLARITY[self.polarity]}, "
            f"bank={bank}, "
            f"unknowns={self.unknowns}, "
            f"raws={binascii.hexlify(self.raw)!r}"
        )


def channel_from_data(
    idx: int, data: bytes | list[int], cflags: bytes | list[int]
) -> Channel:
    # ic(data)
    freq = ((data[2] & 0b00000011) << 16) | (data[1] << 8) | data[0]
    freq_flags = (data[2] & 0b11111100) >> 2
    unknowns = [
        data[4] & 0b11000000,
        data[4] & 0b00001000,
        data[7] & 0b11111110,
        data[10] & 0b01111000,
    ]

    return Channel(
        number=idx,
        freq=decode_freq(freq, freq_flags),
        freq_flags=freq_flags,
        af_filter=bool(data[3] & 0b10000000),
        attenuator=bool(data[3] & 0b01000000),
        mode=(data[3] & 0b00110000) >> 4,
        tuning_step=data[3] & 0b00001111,
        duplex=(data[4] & 0b00110000) >> 4,
        tmode=data[4] & 0b00000111,
        offset=decode_freq((data[6] << 8) | data[5], freq_flags),
        ctone=data[7] & 0b00111111,
        polarity=(data[8] & 0b10000000) >> 7,
        dtsc=(data[8] & 0b01111111),
        canceller_freq=(data[9] << 1) | ((data[10] & 0b10000000) >> 7),
        vsc=bool(data[10] & 0b00000100),
        canceller=bool(data[10] & 0b00000011),
        name=decode_name(data[11:16]),
        hide_channel=bool(cflags[0] & 0b10000000),
        skip=(cflags[0] & 0b01100000) >> 5,
        bank=(cflags[0] & 0b00011111),  # TODO: verify
        bank_pos=cflags[1],  # TODO: verify
        unknowns=unknowns,
        raw=bytes(data),
    )


def bool2bit(val: bool | int, mask: int):
    return mask if val else 0


def set_bits(value: int, newval: int, mask: int) -> int:
    return (value & (~mask)) | (newval & mask)


def channel_to_data(chan: Channel, data: list[int], cflags: list[int]) -> None:
    enc_freq = encode_freq(chan.freq, chan.offset)
    freq0, freq1, freq2 = enc_freq.freq_bytes()
    offset_l, offset_h = enc_freq.offset_bytes()

    # freq
    data[0] = freq0
    data[1] = freq1
    # flags & freq2
    data[2] = (enc_freq.flags << 2) | freq2
    # af_filter, attenuator, mode, tuning_step
    data[3] = (
        bool2bit(chan.af_filter, 0b10000000)
        | bool2bit(chan.attenuator, 0b01000000)
        | (chan.mode & 0b11) << 4
        | (chan.tuning_step & 0b1111)
    )
    # duplex
    data[4] = set_bits(data[4], chan.duplex << 4, 0b00110000)
    # tmode
    data[4] = set_bits(data[4], chan.tmode, 0b00000111)
    # offset
    data[5] = offset_l
    data[6] = offset_h
    # ctone
    data[7] = set_bits(data[7], chan.ctone, 0b00111111)
    # polarity, dtsc
    data[8] = bool2bit(chan.polarity, 0b10000000) | (chan.dtsc & 0b01111111)
    # canceller freq
    data[9] = (chan.canceller_freq & 0b111111110) >> 1
    data[10] = set_bits(data[10], (chan.canceller_freq & 1) << 7, 0b10000000)
    # vsc
    data[10] = set_bits(data[10], chan.vsc << 3, 0b00000100)
    # canceller
    data[10] = set_bits(data[10], chan.canceller, 0b11)
    # name
    data[11:16] = encode_name(chan.name)

    # hide_channel, bank
    cflags[0] = (
        bool2bit(chan.hide_channel, 0b10000000)
        | ((chan.skip & 0b11) << 5)
        | (chan.bank & 0b00011111)
    )
    # bank_pos
    cflags[1] = chan.bank_pos


@dataclass
class Bank:
    idx: int
    name: str
    channels: list[Channel | None]


def bank_from_data(idx: int, data: bytes | list[int]) -> Bank:
    return Bank(
        idx,
        name=bytes(data[0:6]).decode() if data[0] else "",
        channels=[None] * 100,
    )


def bank_to_data(bank: Bank, data: list[int]) -> None:
    data[0:6] = bank.name[:6].ljust(6).encode()


@dataclass
class ScanLink:
    idx: int
    name: str
    edges: list[int]


def scan_link_from_data(idx: int, data: list[int]) -> ScanLink:
    return ScanLink(
        idx=idx,
        name=bytes(data[0:6]).decode() if data[0] else "",
        edges=[],
    )


def scan_link_to_data(sl: ScanLink, data: list[int]) -> None:
    data[0:6] = sl.name[:6].lujust(6).encode()


def scan_link_edges_from_data(data: list[int]) -> list[int]:
    # 4 bytes, with 7bite padding
    mask = (data[3] << 24) | (data[2] << 16) | (data[1] << 8) | data[0]
    edges = []
    for i in range(NUM_SCAN_EDGES):
        if mask & 1:
            edges.append(i)

        mask >>= 1

    return edges


def scan_link_edges_to_data(edges: list[int], data: list[int]) -> None:
    mask = 0
    for e in edges:
        if e:
            mask |= 1

        mask <<= 1

    data[0] = mask & 0xFF
    data[1] = (mask >> 8) & 0xFF
    data[2] = (mask >> 16) & 0xFF
    data[3] = (mask >> 24) & 0xFF


@dataclass
class ScanEdge:
    idx: int
    start: int
    end: int
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


def scan_edge_from_data(idx: int, data: list[int]) -> ScanEdge:
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


def scan_edges_to_data(se: ScanEdge, data: list[int]) -> None:
    start = se.start // 3
    data[0] = start & 0xFF
    data[1] = (start >> 8) & 0xFF
    data[2] = (start >> 16) & 0xFF
    data[3] = (start >> 24) & 0xFF

    end = se.end // 3
    data[4] = end & 0xFF
    data[5] = (end >> 8) & 0xFF
    data[6] = (end >> 16) & 0xFF
    data[7] = (end >> 24) & 0xFF

    data[8] = (
        bool2bit(se.disabled, 0b10000000)
        | (se.mode & 0b111) << 4
        | (se.ts & 0b1111)
    )

    data[9] = set_bits(data[9], se.attn << 4, 0b00110000)

    if se.name:
        data[10:16] = se.name[:6].ljust(6).encode()
    else:
        data[10:16] = [0, 0, 0, 0, 0, 0]


@dataclass
class RarioSettings:
    unk1: list[int]  # 13
    unk13: int
    func_dial_step: int
    unk14: int
    unk15: int
    key_beep: bool
    unk16: int
    beep_level: int
    unk17: int
    back_light: int
    unk18: int
    power_save: bool
    unk19: int
    am_ant: int
    unk20: int
    fm_ant: int
    unk21: list[int]  # 13
    civ_address: int
    unk35: int
    civ_baud_rate: int
    unk37: list[int]  # 15
    unk52: int
    dial_function: bool
    unk52m: int
    mem_display_type: int
    unk54: list[int]  # 11


class RadioMemory:
    def __init__(self) -> None:
        self.mem = [0] * 0x6E60
        self._cache_channels: dict[int, Channel] = {}
        self._cache_banks: dict[int, Bank] = {}

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

    def get_channel(self, idx: int) -> Channel:
        if idx < 0 or idx > NUM_CHANNELS - 1:
            raise IndexError

        if chan := self._cache_channels.get(idx):
            return chan

        start = idx * 16
        data = self.mem[start : start + 16]

        cflags_start = idx * 2 + 0x5F80
        cflags = self.mem[cflags_start : cflags_start + 2]

        chan = channel_from_data(idx, data, cflags)
        self._cache_channels[idx] = chan
        return chan

    def set_channel(self, chan: Channel) -> None:
        idx = chan.number

        self._cache_channels[idx] = chan

        start = idx * 16
        data = self.mem[start : start + 16]

        cflags_start = idx * 2 + 0x5F80
        cflags = self.mem[cflags_start : cflags_start + 2]

        channel_to_data(chan, data, cflags)
        self.mem[start : start + 16] = data
        self.mem[cflags_start : cflags_start + 2] = cflags

    def get_scan_edge(self, idx: int) -> ScanEdge:
        if idx < 0 or idx > NUM_SCAN_EDGES - 1:
            raise IndexError

        start = 0x5DC0 + idx * 16
        data = self.mem[start : start + 16]

        return scan_edge_from_data(idx, data)

    def _get_active_channels(self) -> ty.Iterable[Channel]:
        for cidx in range(NUM_CHANNELS):
            chan = self.get_channel(cidx)
            if not chan.hide_channel and chan.freq:
                yield chan

    def get_bank(self, idx: int) -> Bank:
        if idx < 0 or idx > NUM_BANKS - 1:
            raise IndexError

        if bank := self._cache_banks.get(idx):
            return bank

        start = 0x6D10 + idx * 8
        data = self.mem[start : start + 8]

        bank = bank_from_data(idx, data)

        # TODO: confilicts / doubles
        for chan in self._get_active_channels():
            if chan.bank == idx:
                bank.channels[chan.bank_pos] = chan

        self._cache_banks[idx] = bank

        return bank

    def set_bank(self, bank: Bank) -> None:
        idx = bank.idx
        self._cache_banks[idx] = bank

        start = 0x6D10 + idx * 8
        data = self.mem[start : start + 8]
        bank_to_data(bank, data)

    def get_scan_link(self, idx: int) -> ScanLink:
        if idx < 0 or idx > NUM_SCAN_LINKS - 1:
            raise IndexError

        start = 0x6DC0 + idx * 8
        data = self.mem[start : start + 8]
        sl = scan_link_from_data(idx, data)

        # mapping
        start = 0x6C2C + 4 * idx
        mdata = self.mem[start : start + 4]
        sl.edges = scan_link_edges_from_data(mdata)

        return sl


CODED_CHRS: ty.Final[str] = (
    " ^^^^^^^()*+^-./0123456789:^^=^^^ABCDEFGHIJKLMNOPQRSTUVWXYZ^^^^^"
)
ENCODED_NAME_LEN: ty.Final[int] = 5


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
    if len(inp) != ENCODED_NAME_LEN:
        raise ValueError

    chars = (
        (inp[0] & 0b00001111) << 2 | (inp[1] & 0b11000000) >> 6,
        (inp[1] & 0b00111111),
        (inp[2] & 0b11111100) >> 2,
        (inp[2] & 0b00000011) << 4 | (inp[3] & 0b11110000) >> 4,
        (inp[3] & 0b00001111) << 2 | (inp[4] & 0b11000000) >> 6,
        (inp[4] & 0b00111111),
    )

    return "".join(CODED_CHRS[x] for x in chars)


def encode_name(inp: str) -> list[int]:
    inp = inp[:NAME_LEN].upper().ljust(NAME_LEN)

    iic = [CODED_CHRS.index(x) for x in inp]
    return [
        (iic[0] & 0b00111100) >> 2,  # padding
        ((iic[0] & 0b00000011) << 6) | (iic[1] & 0b00111111),
        ((iic[2] & 0b00111111) << 2) | ((iic[3] & 0b00110000) >> 4),
        ((iic[3] & 0b00001111) << 4) | ((iic[4] & 0b00111100) >> 2),
        ((iic[4] & 0b00000011) << 6) | (iic[5] & 0b00111111),
    ]


def decode_freq(freq: int, flags: int) -> int:
    match flags:
        case 0:
            return 5000 * freq
        case 20:
            return 6250 * freq  # unused
        case 40:
            return (25000 * freq) // 3  # unused?
        case 60:
            return 9000 * freq

    LOG.error("unknown flag %r for freq %r", flags, freq)
    return 0


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
    flags = 0
    if freq % 5000 == freq % 9000 == 0:
        flags = 0 if offset else 60  # 9k step or 50 step
    elif freq % 9000 == 0:
        flags = 60
    elif freq % 5000 == 0:
        flags = 0
    elif freq % 6250 == 0:
        flags = 20
    elif (freq * 3) % 25000 == 0:  # not used?
        flags = 40
    else:
        raise InvalidFlagError

    match flags:
        case 60:  # 9k
            return EncodedFreq(60, freq // 9000, offset // 9000)
        case 40:
            return EncodedFreq(40, freq // 8330, offset // 8330)
        case 20:
            return EncodedFreq(20, freq // 6250, offset // 6250)
        case 0:  # 5k
            return EncodedFreq(0, freq // 5000, offset // 5000)

    raise ValueError


def validate_frequency(inp: str | int) -> bool:
    if isinstance(inp, str):
        try:
            freq = int(inp)
        except ValueError:
            return False
    else:
        freq = inp

    if MAX_FREQUENCY < freq < 0:
        return False

    try:
        encode_freq(freq, 0)
    except ValueError:
        return False

    return True

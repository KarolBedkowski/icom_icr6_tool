# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
# ruff: noqa: PLR2004
"""
Constants used in app.
"""

from __future__ import annotations

import typing as ty
from dataclasses import dataclass
from enum import Enum

MEM_SIZE = 0x6E60
MEM_FOOTER = "IcomCloneFormat3"

NUM_CHANNELS: ty.Final[int] = 1300
NUM_BANKS: ty.Final[int] = 22
NUM_SCAN_EDGES: ty.Final[int] = 25
NUM_SCAN_LINKS: ty.Final[int] = 10
NUM_AUTOWRITE_CHANNELS: ty.Final[int] = 200
NAME_LEN: ty.Final[int] = 6

MIN_FREQUENCY: ty.Final[int] = 100_000
MAX_FREQUENCY: ty.Final[int] = 1_309_995_000
MIN_OFFSET: ty.Final[int] = 5_000
MAX_OFFSET: ty.Final[int] = 159_995_000

TONE_MODES: ty.Final = ["", "TSQL", "TSQL-R", "DTCS", "DTCS-R"]
DUPLEX_DIRS: ty.Final = ["", "-", "+"]
MODES: ty.Final = ["FM", "WFM", "AM", "Auto"]
_MODES_NON_JAP: ty.Final = ["FM", "WFM", "AM"]
_MODES_JAP: ty.Final = ["FM", "WFM", "AM", "Auto"]
# auto is probably not used
# "-" is used only in scanedge
MODES_SCAN_EDGES: ty.Final = ["FM", "WFM", "AM", "Auto", "-"]
STEPS: ty.Final = [
    "5",
    "6.25",
    "8.33",
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
    "Auto",  # not used
    "-",  # used only in scan-edges
]
# used for fill channels
STEPS_KHZ: ty.Final = [
    5000,
    6250,
    8333.3333,
    9000,
    10000,
    12500,
    15000,
    20000,
    25000,
    30000,
    50000,
    100000,
    125000,
    200000,
    0,
    0,
]
_AVAIL_STEPS_NORMAL = [
    "5",
    "6.25",
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
]
_AVAIL_STEPS_NORMAL_JAP = [*_AVAIL_STEPS_NORMAL, "Auto"]
_AVAIL_STEPS_AIR = [
    "5",
    "6.25",
    "8.33",  # added
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
]
_AVAIL_STEPS_AIR_JAP = [*_AVAIL_STEPS_AIR, "Auto"]
_AVAIL_STEPS_BROADCAST = [
    "5",
    "6.25",
    "9",  # added
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
]
_AVAIL_STEPS_BROADCAST_JAP = [*_AVAIL_STEPS_BROADCAST, "Auto"]


# hack; skips on two bits (skip type (S/P) and skip enable (0/1))
SKIPS: ty.Final = ["", "S", "", "P"]
# 31 = not set
BANK_NAMES: ty.Final = "ABCDEFGHIJKLMNOPQRTUWY"
# id when bank is not set in channel
BANK_NOT_SET: ty.Final = 31
POLARITY: ty.Final = ["Normal", "Reverse"]

# https://pl.wikipedia.org/wiki/CTCSS
CTCSS_TONES: ty.Final = (
    "67,0 69,3 71,9 74,4 77,0 79,7 82,5 85,4 88,5 91,5 "
    "94,8 97,4 100,03 103,54 107,25 110,96 114,87 118,88 123,09 127,30 "
    "131,81 136,52 141,33 146,24 151,45 156,76 159,87 162,28 165,59 167,90 "
    "171,31 173,82 177,33 179,94 183,55 186,26 189,97 192,88 196,69 199,50 "
    "203,51 206,52 210,73 218,14 225,75 229,16 233,67 241,88 250,39 254,10"
).split(" ")

DTCS_CODES: ty.Final = (
    "023 025 026 031 032 036 043 047 051 053 "
    "054 065 071 072 073 074 114 115 116 122 "
    "125 131 132 134 143 145 152 155 156 162 "
    "165 172 174 205 212 223 225 226 243 244 "
    "245 246 251 252 255 261 263 265 266 271 "
    "274 306 311 315 325 331 332 343 346 351 "
    "356 364 365 371 411 412 413 423 431 432 "
    "445 446 452 454 455 462 464 465 466 503 "
    "506 516 523 526 532 546 565 606 612 624 "
    "627 631 632 654 662 664 703 712 723 731 "
    "732 734 743 754"
).split(" ")

CANCELLER: ty.Final = ["Off", "Train1", "Train2", "MSK"]
CANCELLER_MIN_FREQ: ty.Final = 300
CANCELLER_MAX_FREQ: ty.Final = 3000

SETT_FUNC_DIAL_STEP: ty.Final = ["100kHz", "1MHz", "10MHz"]
SETT_DIAL_FUNCTION: ty.Final = ["Tuning", "Volume"]
SETT_BEEP_LEVEL: ty.Final = ["Volume", *map(str, range(40))]
SETT_BACKLIGHT: ty.Final = ["Off", "On", "Auto 1", "Auto 2"]
SETT_MEM_DISPLAY_TYPE: ty.Final = [
    "Frequency",
    "Bank name",
    "Memory name",
    "Channel number",
]
SETT_AM_ANT: ty.Final = ["External", "Bar"]
SETT_FM_ANT: ty.Final = ["External", "Earphone"]
SETT_LCD_CONTRAST: ty.Final = list("12345")
SETT_KEY_LOCK: ty.Final = ["Normal", "No SQL", "No Vol", "ALL"]
SETT_MONITOR: ty.Final = ["Push", "Hold"]
SETT_CHARGER_TYPE: ty.Final = [
    "CHG1 (stop after 15h)",
    "CHG2 (continue after 15h)",
]
SETT_PAUSE_TIMER: ty.Final = [f"{x}sec" for x in range(2, 22, 2)] + ["Hold"]
SETT_RESUME_TIMER: ty.Final = [f"{x}sec" for x in range(6)] + ["Hold"]
SETT_CIV_BAUD_RATE: ty.Final = [
    "300bps",
    "1200bps",
    "4800bps",
    "9600bps",
    "19200bps",
    "Auto",
]


# list of valid characters
VALID_CHAR: ty.Final = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789()*+-./:= "
# list of coded characters; ^ is invalid character
CODED_CHRS: ty.Final[str] = (
    " ^^^^^^^()*+^-./0123456789:^^=^^^ABCDEFGHIJKLMNOPQRSTUVWXYZ^^^^^"
)
ENCODED_NAME_LEN: ty.Final[int] = 5

MAX_NAME_LEN: ty.Final = 6
MAX_COMMENT_LEN: ty.Final = 16

# used in scanedge
ATTENUATOR: ty.Final = ["On", "Off", "-"]

WX_CHANNELS = list(map(str, range(1, 11)))

# exclusive; used only when unprotected_frequency_flag is False; so for now
# can be ignored
_BLOCKED_FREQ_USA: ty.Final = [
    (823_995_000, 851_000_000),
    (866_995_000, 896_000_000),
]

_BLOCKED_FREQ_FR: ty.Final = [
    (30000000, 50199999),
    (51200001, 87499999),
    (108000000, 143999999),
    (146000001, 429999999),
    (440000001, 1239999999),
    (1300000001, 1310000000),
]

_BLOCKED_FREQ_JAP: ty.Final = [
    (252900000, 255099999),
    (261900000, 266099999),
    (270900000, 275099999),
    (379900000, 382099999),
    (411900000, 415099999),
    (809900000, 834099999),
    (859900000, 889099999),
    (914900000, 960099999),
]


def tuning_steps_for_freq(freq: int, region: Region) -> list[str]:
    """From manual: additional steps become selectable in only the
    VHF Air band (8.33 kHz) and in the AM broadcast band (9 kHz).
    For Japan is available "Auto" tuning step.
    """
    if 500_000 <= freq <= 1_620_000:
        return region.ts_broadcast

    if 118_000_000 <= freq <= 135_995_000:
        return region.ts_air

    return region.ts_other


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


def is_air_band(freq: int) -> bool:
    return 108_000_000 <= freq <= 136_991_666


def is_broadcast_band(freq: int) -> bool:
    return 495_000 <= freq <= 1_620_000


def default_tuning_step_for_freq(freq: int) -> int:
    if 500_000 <= freq <= 1_620_000:
        return STEPS.index("9")

    if 770_000_000 <= freq <= 960_000_000:
        return STEPS.index("12.5")

    if 68_000_000 <= freq <= 108_000_000:
        # WFM
        return STEPS.index("50")

    if freq > 30_000_00:
        return STEPS.index("25")

    return STEPS.index("5")


# predefined bands
# Japan, Brazil
_BANDS_JAP: ty.Final = [
    495_000,
    1_625_000,
    30_000_000,
    76_000_000,
    108_000_000,
    137_000_000,
    255_100_000,
    382_100_000,
    769_800_000,
    960_100_000,
    1310_000_000,
]

# predefined bands
# France probably
_BANDS_FRANCE: ty.Final = [
    495_000,
    1_625_000,
    30_000_000,
    87_500_000,
    108_000_000,
    137_000_000,
    255_100_000,
    382_100_000,
    769_800_000,
    960_100_000,
    1310_000_000,
]

# Americas
_BANDS_DEFAULT: ty.Final = [
    495_000,
    1_625_000,
    30_000_000,
    88_000_000,
    108_000_000,
    137_000_000,
    255_100_000,
    382_100_000,
    769_800_000,
    960_100_000,
    1310_000_000,
]


@dataclass
class RegionDataMixin:
    # Map region to etcdata; this may be inaccurate as i.e. Japan uses
    # probably more that one etcdata code; also there are also unknown flags.
    etcdata: str
    bands: list[int]
    blocked_freq: list[tuple[int, int]]
    modes: list[str]
    # tuning step
    ts_broadcast: list[str]
    ts_air: list[str]
    ts_other: list[str]


class Region(RegionDataMixin, Enum):
    # global model, no restrictions
    GLOBAL = (  # type: ignore
        "001A",
        _BANDS_DEFAULT,
        [],
        _MODES_NON_JAP,
        _AVAIL_STEPS_BROADCAST,
        _AVAIL_STEPS_AIR,
        _AVAIL_STEPS_NORMAL,
    )
    # unknown
    GLOBAL2 = (  # type: ignore
        "002A",
        _BANDS_DEFAULT,
        [],
        _MODES_NON_JAP,
        _AVAIL_STEPS_BROADCAST,
        _AVAIL_STEPS_AIR,
        _AVAIL_STEPS_NORMAL,
    )
    # gaps 30-50.2 51.2-87.5 108-144 146-430 440-1240 1300-1310
    FRANCE = (
        "01D2",
        _BANDS_FRANCE,
        _BLOCKED_FREQ_FR,
        _MODES_NON_JAP,
        _AVAIL_STEPS_BROADCAST,
        _AVAIL_STEPS_AIR,
        _AVAIL_STEPS_NORMAL,
    )
    # gaps: 824-851, 867-896
    USA = (
        "00AB",
        _BANDS_DEFAULT,
        _BLOCKED_FREQ_USA,
        _MODES_NON_JAP,
        _AVAIL_STEPS_BROADCAST,
        _AVAIL_STEPS_AIR,
        _AVAIL_STEPS_NORMAL,
    )
    # other? Japan - 253-255, 262-266, 271-275, 380-382, 412-415, 810-834,
    # 860-889, 915-950
    JAPAN = (
        "0003",
        _BANDS_JAP,
        _BLOCKED_FREQ_JAP,
        _MODES_JAP,
        _AVAIL_STEPS_BROADCAST_JAP,
        _AVAIL_STEPS_AIR_JAP,
        _AVAIL_STEPS_NORMAL_JAP,
    )

    def __repr__(self) -> str:
        return f"<Region:{self.name}>"


# fmt: off
MONITOR_VOLUME_STEPS = [
    5, 12, 18, 25, 31, 37, 44, 50, 57, 63, 69, 76, 82, 89, 95, 101,
    108, 114, 121, 127, 133, 140, 146, 153, 159, 165, 172, 178, 185,
    191, 197, 204, 210, 217, 223, 229, 236, 242, 249, 255,
]
# fmt: on
MONITOR_SQUELCH_STEPS = [22, 45, 69, 92, 115, 139, 162, 185, 208, 231, 255]
MONITOR_SQUELCH_LEVEL = ["OPEN", "AUTO", *(f"LEVEL{i}" for i in range(1, 10))]
MONITOR_SMETER_STEPS = [0, 16, 48, 80, 112, 144, 160]
MONITOR_SMETER_LEVEL = ["-", "1", "3", "5", "7", "9", "FULL"]
MONITOR_ANTENNA = ["External", "Bar/Earphone"]

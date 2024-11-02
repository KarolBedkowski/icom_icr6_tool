# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import typing as ty

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

TONE_MODES: ty.Final = ["", "TSQL", "TSQL-R", "DTCS", "DTCS-R", "", "", ""]
DUPLEX_DIRS: ty.Final = ["", "-", "+", ""]
MODES: ty.Final = ["FM", "WFM", "AM", "Auto", "-"]
STEPS: ty.Final = [
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
SKIPS: ty.Final = ["", "S", "", "P"]
# 31 = not set
BANK_NAMES: ty.Final = "ABCDEFGHIJKLMNOPQRTUWY"
# id when bank is not set in channel
BANK_NOT_SET: ty.Final = 31
POLARITY: ty.Final = ["Reverse", "Normal"]

# https://pl.wikipedia.org/wiki/CTCSS
CTCSS_TONES: ty.Final = [
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
]

DTCS_CODES: ty.Final = [
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

SETT_FUNC_DIAL_STEP: ty.Final = ["100kHz", "1MHz", "10MHz"]
SETT_DIAL_FUNCTION: ty.Final = ["Tuning", "Volume"]
SETT_BEEP_LEVEL: ty.Final = [str(x) for x in range(40)] + ["Volume"]
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
SETT_CHARGE_TYPE: ty.Final = ["Type 1", "Type 2"]
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

# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
# pylint: disable=protected-access,unspecified-encoding,consider-using-with
# mypy: allow-untyped-defs, allow-untyped-calls
# ruff: noqa: SLF001,PLR2004

""" """

import binascii
from contextlib import suppress

import pytest

with suppress(ImportError):
    import icecream

    icecream.install()

from . import consts, model


@pytest.mark.parametrize(
    "inp",
    [
        b"e9030020000000080072000ba5c21b00",
        b"f4030020000000080072000d7a8a5ae9",
        b"9f040020000000080072000cecbf686b",
        b"a6040020000000080072000d21a77351",
        b"a9040020000000080072000ba5d28353",
        b"ab0400200000000800720008efb35b62",
        b"b00400200000000800720008f58a1351",
        b"b4040020000000080072000d35cab979",
        b"b7040020000000080072000daf84d440",
        b"b80400200000000800720008e1b8f9e5",
    ],
)
def test_encode_decode_channel(inp):
    data = list(binascii.unhexlify(inp))
    cflags = [0, 0]

    chan = model.Channel.from_data(0, data, cflags)

    new_data = list(binascii.unhexlify(b"c706f020000000080072000a73ca196c"))
    new_cflags = [1, 1]

    chan.to_data(new_data, new_cflags)

    assert data == new_data
    assert cflags == new_cflags


class TestDecodeChannel:
    def test_decode1(self):
        data = bytearray(
            binascii.unhexlify(b"E9030020000000080072000BA5C21B00")
        )
        cflags = bytearray(b"\x01\x00")

        chan = model.Channel.from_data(100, data, cflags)
        assert chan.freq == 5005000
        assert chan.freq_flags == 0
        assert chan.name == "NEPAL"
        assert consts.MODES[chan.mode] == "AM"
        assert not chan.af_filter
        assert not chan.attenuator
        assert consts.STEPS[chan.tuning_step] == "5"
        assert consts.DUPLEX_DIRS[chan.duplex] == ""
        assert chan.offset == 0
        assert consts.TONE_MODES[chan.tone_mode] == ""
        assert consts.CTCSS_TONES[chan.tsql_freq] == "88,5"
        assert consts.POLARITY[chan.polarity] == "Normal"
        assert consts.DTCS_CODES[chan.dtsc] == "023"
        assert not chan.vsc
        assert consts.CANCELLER[chan.canceller] == "Off"
        assert chan.canceller_freq == 2280
        assert not chan.hide_channel
        assert consts.SKIPS[chan.skip] == ""
        assert chan.bank == 1
        assert chan.bank_pos == 0

    def test_decode2(self):
        data = bytearray(
            binascii.unhexlify(b"0a8b0205146009028472000935c0d000")
        )
        cflags = bytearray(b"\x01\x00")

        chan = model.Channel.from_data(25, data, cflags)
        assert chan.number == 25
        assert chan.freq == 833_330_000
        assert chan.freq_flags == 0
        assert chan.name == "DUP-"
        assert consts.MODES[chan.mode] == "FM"
        assert not chan.af_filter
        assert not chan.attenuator
        assert consts.STEPS[chan.tuning_step] == "12.5"
        assert consts.DUPLEX_DIRS[chan.duplex] == "-"
        assert chan.offset == 12_000_000
        assert consts.TONE_MODES[chan.tone_mode] == "DTCS-R"
        assert consts.CTCSS_TONES[chan.tsql_freq] == "71,9"
        assert consts.POLARITY[chan.polarity] == "Reverse"
        assert consts.DTCS_CODES[chan.dtsc] == "032"
        assert not chan.vsc
        assert consts.CANCELLER[chan.canceller] == "Off"
        assert chan.canceller_freq == 2280
        assert not chan.hide_channel
        assert consts.SKIPS[chan.skip] == ""
        assert chan.bank == 1
        assert chan.bank_pos == 0

    def test_decode3(self):
        data = bytearray(
            binascii.unhexlify(b"282300c82420032cba72040d25cf4452")
        )
        cflags = bytearray(binascii.unhexlify(b"732b"))

        chan = model.Channel.from_data(99, data, cflags)
        assert chan.number == 99
        assert chan.freq == 45_000_000
        assert chan.freq_flags == 0
        assert chan.name == "TEST12"
        assert consts.MODES[chan.mode] == "FM"
        assert chan.af_filter
        assert chan.attenuator
        assert consts.STEPS[chan.tuning_step] == "25"
        assert consts.DUPLEX_DIRS[chan.duplex] == "+"
        assert chan.offset == 4_000_000
        assert consts.TONE_MODES[chan.tone_mode] == "DTCS-R"
        assert consts.CTCSS_TONES[chan.tsql_freq] == "225,75"
        assert consts.POLARITY[chan.polarity] == "Reverse"
        assert consts.DTCS_CODES[chan.dtsc] == "346"
        assert chan.vsc
        assert consts.CANCELLER[chan.canceller] == "Off"
        assert chan.canceller_freq == 2280
        assert not chan.hide_channel
        assert consts.SKIPS[chan.skip] == "P"
        assert consts.BANK_NAMES[chan.bank] == "U"
        assert chan.bank_pos == 43


@pytest.mark.parametrize(
    ("inp", "exp"),
    [
        ([0b00101001, 0b01001101, 0b00011011], "A  D F  I KL  O QR UW "),
        ([0b10101010, 0b10100100, 0b00100101], " B D F H  K  N PQ T  Y"),
    ],
)
def test_bank_links(inp, exp):
    bl = model.BankLinks.from_data(inp)
    assert bl.human() == exp
    data = [0, 0, 0]
    bl.to_data(data)

    assert data == inp

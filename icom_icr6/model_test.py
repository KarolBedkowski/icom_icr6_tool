# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
# pylint: disable=protected-access,unspecified-encoding,consider-using-with
# mypy: allow-untyped-defs, allow-untyped-calls
# ruff: noqa: SLF001

""" """

import binascii

import pytest

from . import model


@pytest.mark.parametrize(
    ("freq", "offset", "exp_freq", "exp_flags"),
    [
        (45000000, 0, 5000, 60),
        (45000000, 1, 9000, 0),
        (90000000, 0, 10000, 60),
        (831250, 0, 133, 20),
        (1309995000, 0, 145555, 60),
        (100000, 0, 20, 0),
    ],
)
def test_encode_freq(freq, offset, exp_freq, exp_flags):
    res = model.encode_freq(freq, offset)
    assert res.freq == exp_freq
    assert res.flags == exp_flags


@pytest.mark.parametrize(
    ("inp", "encoded"),
    [
        ("TE    ", b"\x0d\x25\x00\x00\x00"),
        ("FSDFS ", b"\x09\xb3\x92\x6c\xc0"),
        ("UZBEKI", b"\x0d\x7a\x8a\x5a\xe9"),
        ("NETH-3", b"\x0b\xa5\xd2\x83\x53"),
        ("CAN/GE", b"\x08\xe1\xb8\xf9\xe5"),
    ],
)
def test_encode_decode_name(inp, encoded):
    enc = model.encode_name(inp)
    assert enc == list(encoded)

    dec = model.decode_name(encoded)
    assert dec == inp


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

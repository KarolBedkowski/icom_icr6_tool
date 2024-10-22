# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

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

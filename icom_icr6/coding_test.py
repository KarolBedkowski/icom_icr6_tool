# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
# pylint: disable=protected-access,unspecified-encoding,consider-using-with
# mypy: allow-untyped-defs, allow-untyped-calls
# ruff: noqa: SLF001,PLR2004

""" """

from contextlib import suppress

import pytest

with suppress(ImportError):
    import icecream

    icecream.install()

from . import coding


@pytest.mark.parametrize(
    ("freq", "offset", "exp_freq", "exp_flags"),
    [
        (45000000, 0, 9000, 0),
        (45000000, 1, 9000, 0),
        (90000000, 0, 18000, 0),
        (831250, 0, 133, 0b0101),
        (831250, 1, 133, 0b0001),
        (1309995000, 0, 261999, 0b0),
        (100000, 0, 20, 0b0),
        (100000, 1, 20, 0b0),
        (1_620_000, 0, 180, 0b1111),
        (1_620_000, 1, 324, 0b0),
        (1_611_000, 0, 179, 0b1111),
        (1_611_000, 1, 179, 0b0011),
    ],
)
def test_encode_freq(freq, offset, exp_freq, exp_flags):
    res = coding.encode_freq(freq, offset)
    assert res.freq == exp_freq
    assert res.flags == exp_flags


@pytest.mark.parametrize(
    ("inp", "encoded"),
    [
        ("TE", b"\x0d\x25\x00\x00\x00"),
        ("FSDFS", b"\x09\xb3\x92\x6c\xc0"),
        ("UZBEKI", b"\x0d\x7a\x8a\x5a\xe9"),
        ("NETH-3", b"\x0b\xa5\xd2\x83\x53"),
        ("CAN/GE", b"\x08\xe1\xb8\xf9\xe5"),
    ],
)
def test_encode_decode_name(inp, encoded):
    enc = coding.encode_name(inp)
    assert enc == list(encoded)

    dec = coding.decode_name(encoded)
    assert dec == inp

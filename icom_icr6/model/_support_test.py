# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
# pylint: disable=protected-access,unspecified-encoding,consider-using-with
# mypy: allow-untyped-defs, allow-untyped-calls
# ruff: noqa: SLF001,PLR2004, FBT003

""" """

import pytest

from icom_icr6.model import _support


@pytest.mark.parametrize(
    ("inp", "exp"),
    [
        (1, "1"),
        (5, "5"),
        (8, "<[8]>"),
    ],
)
def test_try_get(inp, exp):
    seq = ["0", "1", "2", "3", "4", "5"]
    assert _support.try_get(seq, inp) == exp


@pytest.mark.parametrize(
    ("inp", "default", "exp"),
    [
        ("1", -1, 0),
        ("a", -2, -2),
        ("5", 0, 4),
    ],
)
def test_get_index_or_default(inp, exp, default):
    seq = ["1", "2", "3", "4", "5"]
    assert _support.get_index_or_default(seq, inp, default) == exp


def test_obj2bool():
    assert _support.obj2bool("yes")
    assert _support.obj2bool("YES")
    assert _support.obj2bool("Y")
    assert _support.obj2bool("y")
    assert _support.obj2bool("TRUE")
    assert _support.obj2bool("True")
    assert _support.obj2bool("t")
    assert not _support.obj2bool("false")
    assert not _support.obj2bool("No")
    assert not _support.obj2bool("no")
    assert not _support.obj2bool("f")
    assert not _support.obj2bool("False")

    assert _support.obj2bool(True)
    assert not _support.obj2bool(False)

    assert _support.obj2bool(1)
    assert not _support.obj2bool(0)

    assert not _support.obj2bool("abc")
    assert not _support.obj2bool("")


def test_bool2bit():
    assert _support.bool2bit(True, 0xF1) == 0xF1
    assert _support.bool2bit(False, 0xF1) == 0
    assert _support.bool2bit(1, 0x1) == 1
    assert _support.bool2bit(0, 0x3) == 0


def test_data_set_bit():
    data = bytearray([1] * 4)

    _support.data_set_bit(data, 0, 3, True)

    _support.data_set_bit(data, 1, 5, True)

    _support.data_set_bit(data, 1, 2, False)

    _support.data_set_bit(data, 2, 0, False)

    _support.data_set_bit(data, 3, 1, True)
    _support.data_set_bit(data, 3, 3, True)
    _support.data_set_bit(data, 3, 5, True)

    assert data[0] == 0b00001001
    assert data[1] == 0b00100001
    assert data[1] == 0b00100001
    assert data[2] == 0b00000000
    assert data[3] == 0b00101011


def test_data_set():
    data = bytearray([0b01010101] * 5)

    _support.data_set(data, 0, 0b00001111, 0)
    _support.data_set(data, 1, 0b00001111, 0b1101)
    _support.data_set(data, 2, 0b10101111, 0b0)
    _support.data_set(data, 3, 0b11101111, 0b0)
    _support.data_set(data, 4, 0b11101111, 0b11111111)
    assert data[0] == 0b01010000
    assert data[1] == 0b01011101
    assert data[2] == 0b01010000
    assert data[3] == 0b00010000
    assert data[4] == 0b11111111

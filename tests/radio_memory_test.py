# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
# pylint: disable=protected-access,unspecified-encoding,consider-using-with
# mypy: allow-untyped-defs, allow-untyped-calls
# ruff: noqa: SLF001,PLR2004

""" """

import pytest

from icom_icr6 import consts, radio_memory as rm


@pytest.mark.parametrize(
    ("inp", "exp"),
    [
        ("0003", consts.Region.JAPAN),
        ("001A", consts.Region.GLOBAL),
        ("002A", consts.Region.GLOBAL2),
        ("00AB", consts.Region.USA),
    ],
)
def test_region_from_etcdata(inp, exp):
    assert rm.region_from_etcdata(inp) == exp


@pytest.mark.parametrize(
    ("region", "flags", "exp"),
    [
        (0, 1, 0x03),
        (1, 1, 0x1A),
        (1, 2, 0b00000000_00011100),
        (1, 3, 0b00000000_00011111),
        (2, 1, 0x2A),
        (6, 1, 0xAB),
        (13, 1, 0x01D2),
        (13, 2, 0b00000001_11010100),
        (13, 3, 0b00000001_11010111),
    ],
)
def test_etcdata_from_region(region, flags, exp):
    etcdata = rm.etcdata_from_region(region, flags)
    assert etcdata == exp
    assert rm.etcdata_to_region_flags(etcdata) == (region, flags)

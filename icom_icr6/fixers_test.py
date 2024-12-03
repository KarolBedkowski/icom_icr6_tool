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

from . import fixers


@pytest.mark.parametrize(
    ("inp", "usa", "exp"),
    [
        (100_000, False, 100_000),
        (100_000, True, 100_000),
        (100_001, False, 100_000),
        (123_123_123_123, False, 1_309_995_000),
        (0, False, 100_000),
        (12_123_000, False, 12_125_000),
        (912_340, False, 912_500),
        (451_000, False, 450_000),
        (459_000, False, 460_000),
        (512_400, False, 512_500),
        (512_550, False, 512_500),
        (823_995_100, False, 823_995_000),
        (824_000_000, True, 823_995_000),
        (850_000_000, True, 851_000_000),
        (124_991_666, False, 124_991_666),
        (124_991_665, False, 124_991_666),
        (124_991_667, False, 124_991_666),
        # (120_024_999, False, 120_020_000),
        (120_016_666, False, 120_016_666),
        (120_008_330, False, 120_008_333),
        (120_008_333, False, 120_008_333),
        (120_022_500, False, 120_020_000),
    ],
)
def test_fix_freq(inp, usa, exp):
    freq = fixers.fix_frequency(inp, usa_model=usa)
    assert freq == exp


@pytest.mark.parametrize(
    ("freq", "offset", "exp_offset"),
    [
        # 'ff': 0, 'freq': 20, 'offset': 20,
        (100_000, 100_000, 100_000),
        # 'ff': 0, 'freq': 20, 'offset': 125,
        (100_000, 625_000, 625_000),
        # 'ff': 0101, 'freq': 16, 'offset': 133
        (100_000, 831_000, 831_250),
        # ff: 00000 'freq': 20, 'offset': 246
        (100_000, 1_230_000, 1_230_000),
        # 'ff': 101, 'freq': 16, 'offset': 197
        (100_000, 1_231_333, 1_231_250),
        (100_000, 1_232_000, 1_231_250),
        (100_000, 1_233_000, 1_233_000),
        (100_000, 1_233_300, 1_235_000),
        # 'ff': 0, 'freq': 20, 'offset': 247
        (100_000, 1_233_333, 1_235_000),
        (100_000, 1_234_000, 1_235_000),
        # 'ff': 0011, 'freq': 131, 'offset': 20,
        (1_179_000, 100_000, 100_000),
        # 'ff': 11, 'freq': 131, 'offset': 125,
        (1_179_000, 625_000, 625_000),
        # 'ff': 0111, 'freq': 131, 'offset': 133
        (1_179_000, 831_000, 831_250),
        # ff=0011 'freq': 131, 'offset': 246,
        (1_179_000, 1_230_000, 1_230_000),
        # 'ff': 0101, 'freq': 133, 'offset': 16
        (831_2500, 100_000, 100_000),
        # 'ff': 0101, 'freq': 133, 'offset': 100
        (831_2500, 625_000, 625_000),
        # 'ff': 0101, 'freq': 133, 'offset': 133
        (831_2500, 831_000, 831_250),
        # 'ff': 0001, 'freq': 133, 'offset': 247
        (831_2500, 1_233_333, 1_235_000),
        # 'ff': 0001, 'freq': 133, 'offset': 247
        (831_2500, 1_234_000, 1_235_000),
    ],
)
def test_fix_offset(freq, offset, exp_offset):
    fixed_off = fixers.fix_offset(freq, offset)
    assert fixed_off == exp_offset

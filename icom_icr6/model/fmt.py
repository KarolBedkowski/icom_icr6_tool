# Copyright © 2025 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import typing as ty

MAX_FLOAT_FREQ: ty.Final = 1400.0
MAX_FLOAT_OFFSET: ty.Final = 160.0


def _parse_frequency(o: object, max_float: float) -> int:
    val = 0.0

    if isinstance(o, int):
        val = o

    elif isinstance(o, str):
        val = float(o.replace(" ", "").replace(",", "."))

    elif isinstance(o, float):
        val = o

    else:
        val = float(o)  # type: ignore

    return int(val * 1_000_000 if 0 < val < max_float else val)


def parse_freq(o: object, **_kwargs: object) -> int:
    return _parse_frequency(o, MAX_FLOAT_FREQ)


def parse_offset(o: object, **_kwargs: object) -> int:
    return _parse_frequency(o, MAX_FLOAT_OFFSET)


def format_freq(freq: int, **_kwargs: object) -> str:
    return f"{freq:_}".replace("_", " ")

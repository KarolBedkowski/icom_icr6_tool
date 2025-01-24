# Copyright © 2025 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """


def _parse_frequency(o: object) -> float:
    val = 0.0

    if isinstance(o, int):
        val = o
    elif isinstance(o, str):
        val = float(o.replace(" ", "").replace(",", "."))
    elif isinstance(o, float):
        val = o
    else:
        val = float(o)  # type: ignore

    return val


def parse_freq(o: object, **_kwargs: object) -> int:
    val = _parse_frequency(o)
    return int(val * 1_000_000 if 0 < val < 1400.0 else val)  # noqa:PLR2004


def parse_offset(o: object, **_kwargs: object) -> int:
    return int(_parse_frequency(o))


def format_freq(freq: int, **_kwargs: object) -> str:
    return f"{freq:_}".replace("_", " ")

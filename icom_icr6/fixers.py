# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import typing as ty
import unicodedata

from . import consts


def _first_min_diff(base: float, values: ty.Iterable[int]) -> float:
    minimal = base
    err = 99999999999.0
    # keep order; using min not always return first minimal value
    for v in values:
        if (nerr := abs(base - v)) < err:
            err = nerr
            minimal = v

    return minimal


def _fix_frequency(freq: int, base_freq: int) -> int:
    """base_freq is channel frequency;
    freq is channel freq or offset to correct
    """
    # try exact match
    if not freq % 5000 or not freq % 6250:
        return freq

    if consts.is_broadcast_band(base_freq) and not freq % 9000:
        return freq

    if consts.is_air_band(base_freq):
        # TODO: check which work better
        if round(freq * 3 / 25000.0) == freq:
            return freq

        if not freq % 8333 or freq % 10 in (3, 6):
            return freq

    # try find best freq
    f5 = freq // 5000
    f62 = freq // 6250
    nfreqs = [f5 * 5000, (f5 + 1) * 5000, f62 * 6250, (f62 + 1) * 6250]

    # TODO: 9k is not used for rounding?
    if consts.is_broadcast_band(base_freq):
        f9 = freq // 9000
        nfreqs.extend((f9 * 9000, (f9 + 1) * 9000))

    if consts.is_air_band(base_freq):
        f8 = freq * 3 // 25000
        nfreqs.extend(((f8 * 25000) // 3, ((f8 + 1) * 25000) // 3))

    return int(_first_min_diff(freq, nfreqs))


def fix_frequency(
    freq: int, *, blocked_freq: list[tuple[int, int]] | None = None
) -> int:
    # FIXME: usa_model not used
    freq = max(freq, consts.MIN_FREQUENCY)
    freq = min(freq, consts.MAX_FREQUENCY)

    if blocked_freq:
        # if freq is forbidden range; set freq to nearest valid freq.
        for fmin, fmax in blocked_freq:
            if fmin < freq < fmax:
                freq = fmin if (freq - fmin) < (fmax - freq) else fmax
                break

    return _fix_frequency(freq, freq)


def fix_offset(freq: int, offset: int) -> int:
    if offset == 0:
        return 0

    offset = max(offset, consts.MIN_OFFSET)
    offset = min(offset, consts.MAX_OFFSET)

    if offset % 9000 == freq % 9000 == 0:
        # 9k is used only if match exactly
        return offset

    return _fix_frequency(offset, freq)


def fix_name(name: str) -> str:
    name = name.rstrip().upper()
    if not name:
        return ""

    name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "replace").decode()
    )
    name = "".join(c for c in name if c in consts.VALID_CHAR)
    return name[:6]


def fix_comment(name: str) -> str:
    name = name.rstrip()
    if not name:
        return ""

    name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "replace").decode()
    )
    name = "".join(c for c in name if c.upper() in consts.VALID_CHAR)
    return name[:16]


def fix_tuning_step(freq: int, tuning_step: int) -> int:
    if not freq:
        return tuning_step

    ts = consts.STEPS[tuning_step]
    if ts == "9" and not consts.is_broadcast_band(freq):
        return consts.default_tuning_step_for_freq(freq)

    if ts == "8.33" and not consts.is_air_band(freq):
        return consts.default_tuning_step_for_freq(freq)

    return tuning_step

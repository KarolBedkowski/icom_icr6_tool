# Copyright © 2025 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import typing as ty

from . import consts
from .radio_memory import RadioMemory


def generate_sheet(rm: RadioMemory) -> ty.Iterable[str]:
    yield "Banks"

    bl = rm.bank_links
    for b, name in zip(rm.banks, consts.BANK_NAMES, strict=True):
        bl_enabled = "[L]" if bl[b.idx] else "   "
        cnt = sum(1 for _ in rm.get_channels_in_bank(b.idx))
        yield f"{name}: {b.name:<6}  {bl_enabled}  ch: {cnt}"

    yield ""
    yield "Channels groups"
    for g in range(13):
        cnt = sum(1 for _ in rm.get_active_channels_in_group(g))
        yield f"{g:2d}xx:                  ch: {cnt}"

    yield ""
    yield "Scan edges"
    for se in rm.scan_edges:
        if se.hidden:
            yield f"{se.idx:2d}: -"
        else:
            yield (
                f"{se.idx:2d}: {se.name:<6}  "
                f"{consts.MODES_SCAN_EDGES[se.mode]:<4} "
                f"{_format_freq(se.start):>13} - "
                f"{_format_freq(se.end):>13} / {consts.STEPS[se.tuning_step]}"
            )

    yield ""
    yield "Scan links"
    for sl in rm.scan_links:
        cnt = sum(sl.links())
        yield f"{sl.idx}: {sl.name:<6}  edges: {cnt}"


def _format_freq(freq: int, **_kwargs: object) -> str:
    return f"{freq:_}".replace("_", " ")

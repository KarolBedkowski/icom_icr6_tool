# Copyright © 2025 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import typing as ty

from . import config, consts
from .radio_memory import RadioMemory


def generate_sheet(rm: RadioMemory) -> ty.Iterable[str]:
    yield "Banks"

    bl = rm.bank_links
    cnts = _count_channels_in_banks(rm)
    for b, name in zip(rm.banks, consts.BANK_NAMES, strict=True):
        bl_enabled = "[L]" if bl[b.idx] else "   "
        yield f"{name}: {b.name:<6}  {bl_enabled}  ch: {cnts[b.idx]}"

    yield ""
    yield "Channels groups"
    for g in range(13):
        cnt = sum(1 for _ in rm.get_active_channels_in_group(g))
        name = config.CONFIG.chan_group_names[g]
        yield f"{g:2d}xx: {name:<20}  ch: {cnt}"

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


def generate_stats(rm: RadioMemory) -> ty.Iterable[str]:
    yield "Channels"
    yield from _get_data_channels(rm)
    yield ""
    yield "Bands"
    yield from _get_data_bands(rm)
    yield ""
    yield "Banks"
    yield from _get_data_banks(rm)
    yield ""
    yield "Scan edges"
    yield from _get_data_se(rm)
    yield ""
    yield "Scan links"
    yield from _get_data_sl(rm)


def _get_data_channels(rm: RadioMemory) -> ty.Iterable[str]:
    cnt = sum(1 for c in rm.get_active_channels())
    yield f"Total number of active channels: {cnt}"

    cnt = sum(c.bank != consts.BANK_NOT_SET for c in rm.get_active_channels())
    yield f"Total number of active channels in banks: {cnt}"

    cnt = sum(c.bank == consts.BANK_NOT_SET for c in rm.get_active_channels())
    yield f"Total number of active channels without bank: {cnt}"

    cnt = len(rm.awchannels)
    yield f"Number of autowrite channels: {cnt}"


def _get_data_bands(rm: RadioMemory) -> ty.Iterable[str]:
    prev_band = 100_000
    for band in rm.region.bands():
        cnt = sum(
            1 for c in rm.get_active_channels() if prev_band <= c.freq < band
        )
        yield (
            f"Channels in {_format_freq(prev_band):>13} - "
            f"{_format_freq(band):>13}:  {cnt}"
        )
        prev_band = band


def _get_data_banks(rm: RadioMemory) -> ty.Iterable[str]:
    cnts = _count_channels_in_banks(rm)
    for idx, bank in enumerate(rm.banks):
        yield f"{idx:2d}: {bank.name:<6}  channels: {cnts[idx]}"


def _get_data_se(rm: RadioMemory) -> ty.Iterable[str]:
    for se in rm.scan_edges:
        if se.hidden:
            continue

        in_sl = sum(sl[se.idx] for sl in rm.scan_links)
        yield f"{se.idx:2d}: {se.name:<6}  scan links: {in_sl}"


def _get_data_sl(rm: RadioMemory) -> ty.Iterable[str]:
    for sl in rm.scan_links:
        cnt = sum(sl.links())
        yield f"{sl.idx}: {sl.name:<6}  edges: {cnt}"


def _format_freq(freq: int, **_kwargs: object) -> str:
    return f"{freq:_}".replace("_", " ")


def _count_channels_in_banks(rm: RadioMemory) -> dict[int, int]:
    cnts = {b: 0 for b in range(consts.NUM_BANKS)}
    cnts[consts.BANK_NOT_SET] = 0

    for c in rm.get_active_channels():
        cnts[c.bank] += 1

    return cnts

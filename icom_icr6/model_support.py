# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import typing as ty

from . import model


def sort_channels(
    channels: list[model.Channel | None] | list[model.Channel], field: str
) -> None:
    sfunc: ty.Callable[[model.Channel | None], str | int]

    match field:
        case "name":
            sfunc = _sort_func_name

        case "name2":
            sfunc = _sort_func_name2

        case "freq":
            sfunc = _sort_func_freq

        case "pack":
            sfunc = _sort_func_pack

        case "channel":
            sfunc = _sort_func_channel

        case _:
            raise ValueError

    channels.sort(key=sfunc)


def _sort_func_name(chan: model.Channel | None) -> str:
    return chan.name or "\xf0" if chan and not chan.hide_channel else "\xff"


def _sort_func_name2(chan: model.Channel | None) -> str:
    return chan.name or "" if chan and not chan.hide_channel else "\xff"


def _sort_func_freq(chan: model.Channel | None) -> int:
    return chan.freq if chan and not chan.hide_channel else 9_999_999_999


def _sort_func_pack(chan: model.Channel | None) -> int:
    return 0 if chan and not chan.hide_channel else 1


def _sort_func_channel(chan: model.Channel | None) -> int:
    return chan.number if chan and not chan.hide_channel else 1400

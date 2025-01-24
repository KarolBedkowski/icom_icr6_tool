# Copyright © 2025 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import typing as ty

from .channels import Channel


def sort_channels(
    channels: list[Channel | None] | list[Channel], field: str
) -> None:
    sfunc: ty.Callable[[Channel | None], str | int]

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


def _sort_func_name(chan: Channel | None) -> str:
    return chan.name or "\xf0" if chan and not chan.hide_channel else "\xff"


def _sort_func_name2(chan: Channel | None) -> str:
    return chan.name or "" if chan and not chan.hide_channel else "\xff"


def _sort_func_freq(chan: Channel | None) -> int:
    return chan.freq if chan and not chan.hide_channel else 9_999_999_999


def _sort_func_pack(chan: Channel | None) -> int:
    return 0 if chan and not chan.hide_channel else 1


def _sort_func_channel(chan: Channel | None) -> int:
    return chan.number if chan and not chan.hide_channel else 1400

#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
# ruff: noqa: PLR2004

""" """

import logging
import sys
from contextlib import suppress
from pathlib import Path
import typing as ty

from . import gui, io

with suppress(ImportError):
    import icecream

    icecream.install()
    ic = icecream.ic


LOG = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG)


def main_clone_from_radio() -> None:
    """cmd: clone_from_radio
    args: <port> <icf file>
    """
    if len(sys.argv) < 4:
        print("port and file name required")
        return

    radio = io.Radio(sys.argv[2])
    mem = radio.clone_from()
    io.save_icf_file(Path(sys.argv[3]), mem)


def main_radio_info() -> None:
    """cmd: radio_info
    args: <port>
    """
    if len(sys.argv) < 3:
        print("port required (/dev/ttyUSB0 ie)")
        return

    radio = io.Radio(sys.argv[2])
    if model := radio.get_model():
        print(f"Model: {model!r}")
        print(f"Is IC-R6: {model.is_icr6()}")
    else:
        print("ERROR")


def main_print_channels() -> None:
    """cmd: channels
    args: <icf file> [<start channel num>] [hidden]"""
    if len(sys.argv) < 3:
        print("file name required")
        return

    mem = io.load_icf_file(Path(sys.argv[2]))

    hidden = False
    if "hidden" in sys.argv:
        sys.argv.remove("hidden")
        hidden = True

    print("Channels")
    ch_start, ch_end = 0, 1300
    if len(sys.argv) >= 4:
        ch_start = int(sys.argv[3]) * 100
        ch_end = ch_start + 100

    for channel in range(ch_start, ch_end):
        ch = mem.get_channel(channel)
        if not ch.hide_channel or not ch.freq or hidden:
            print(channel, ch)


def main_print_aw_channels() -> None:
    """cmd: autowrite
    args: <icf file>
    """
    if len(sys.argv) < 3:
        print("file name required")
        return

    mem = io.load_icf_file(Path(sys.argv[2]))

    print("Autowrite channels")
    for channel in sorted(mem.get_autowrite_channels()):
        print(channel, channel)


def main_print_banks() -> None:
    """cmd: banks
    args: <icf file>
    """
    if len(sys.argv) < 3:
        print("file name required")
        return

    mem = io.load_icf_file(Path(sys.argv[2]))

    print("Banks")
    for idx in range(22):
        print(idx, mem.get_bank(idx), mem.get_bank_channels(idx))


def main_print_scan_programs() -> None:
    """cmd: scan
    args: <icf file>
    """
    if len(sys.argv) < 3:
        print("file name required")
        return

    mem = io.load_icf_file(Path(sys.argv[2]))

    print("Scan links")
    for idx in range(10):
        print(idx, mem.get_scan_link(idx))

    print("Scan edges")
    for idx in range(25):
        print(idx, mem.get_scan_edge(idx))


def main_write_mem_raw() -> None:
    """cmd: icf2raw
    args: <icf file> [<raw file>]
    """
    if len(sys.argv) < 3:
        print("file name required")
        return

    file = Path(sys.argv[2])
    mem = io.load_icf_file(file)

    dst = Path(sys.argv[3]) if len(sys.argv) > 3 else file.with_suffix(".raw")
    io.save_raw_memory(dst, mem)


def main_write_icf_mem() -> None:
    """cmd: raw2icf
    args: <raw file> [<icf file>]
    """
    if len(sys.argv) < 3:
        print("file name required")
        return

    file = Path(sys.argv[2])
    mem = io.load_raw_memory(file)

    dst = Path(sys.argv[3]) if len(sys.argv) > 3 else file.with_suffix(".icf")
    io.save_icf_file(dst, mem)


def main_print_settings() -> None:
    """cmd: settings
    args: <icf file>
    """
    if len(sys.argv) < 3:
        print("file name required")
        return

    file = Path(sys.argv[2])
    mem = io.load_icf_file(file)

    print("Settings")
    sett = mem.get_settings()
    print(repr(sett))

    print("Bank links")
    bl = mem.get_bank_links()
    print(bl)


def get_commands(
    *functions: ty.Callable[[], None],
) -> ty.Iterable[tuple[str, tuple[str, ty.Callable[[], None]]]]:
    for func in functions:
        cmd = ""
        args = ""
        if doc := func.__doc__:
            for line in doc.split("\n"):
                lkey, _, val = line.strip().partition(":")
                if lkey == "args":
                    args = val.strip()
                elif lkey == "cmd" and (v := val.strip()):
                    cmd = v

        if cmd:
            yield cmd, (args, func)


def main_help(cmds: dict[str, tuple[str, ty.Callable[[], None]]]) -> None:
    print(f"""{sys.argv[0]} <command>
Command:""")

    for cmd, (args, _) in cmds.items():
        print(f"   {cmd} {args}")


def main() -> None:
    cmds = dict(
        get_commands(
            main_print_channels,
            main_print_banks,
            main_print_scan_programs,
            main_write_mem_raw,
            main_write_icf_mem,
            main_clone_from_radio,
            main_print_aw_channels,
            main_radio_info,
            main_print_settings,
        )
    )

    if len(sys.argv) == 1:
        main_help(cmds)
    elif cmd := cmds.get(sys.argv[1]):
        cmd[1]()
    else:
        main_help(cmds)


def main_gui() -> None:
    gui.start_gui()

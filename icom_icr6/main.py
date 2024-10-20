#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import sys
from pathlib import Path

import icecream

from . import gui, io

icecream.install()

ic = icecream.ic

LOG = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG)


def main_clone_from_radio() -> None:
    if len(sys.argv) < 3:
        print("file name required")
        return

    radio = io.Radio()
    mem = radio.clone_from()
    io.save_icf_file(Path(sys.argv[2]), mem)


def main_radio_info() -> None:
    radio = io.Radio()
    print(f"Model: {radio.get_model()!r}")


def main_print_channels() -> None:
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


def main_print_banks() -> None:
    if len(sys.argv) < 3:
        print("file name required")
        return

    mem = io.load_icf_file(Path(sys.argv[2]))

    print("Nanks")
    for idx in range(22):
        print(idx, mem.get_bank(idx))


def main_print_scan_programms() -> None:
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
    if len(sys.argv) < 3:
        print("file name required")
        return

    file = Path(sys.argv[2])
    mem = io.load_icf_file(file)

    dst = Path(sys.argv[3]) if len(sys.argv) > 3 else file.with_suffix(".raw")
    io.save_raw_memory(dst, mem)


def main_help() -> None:
    print(f"""{sys.argv[0]} <command>
Command:
   channels <icf file> [<start channel num>] [hidden]
   banks <icf file>
   scan <icf file>
   write_mem <icf file> [<raw file>]
   clone_from_radio <icf file>
   radio_info
""")


def main() -> None:
    if len(sys.argv) == 1:
        main_help()
        return

    match sys.argv[1]:
        case "channels":
            main_print_channels()
        case "banks":
            main_print_banks()
        case "scan":
            main_print_scan_programms()
        case "write_mem":
            main_write_mem_raw()
        case "clone_from_radio":
            main_clone_from_radio()
        case "radio_info":
            main_radio_info()
        case _:
            main_help()


def main_gui() -> None:
    gui.start_gui()

#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
from pathlib import Path

import icecream

from . import gui, io, model

icecream.install()

ic = icecream.ic

LOG = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG)


def main1() -> None:
    # f = Frame(0, b'014020E89502CF30FF7CFFFF72000FFFFFFFFFE89502CF30FF7CFFFF72000FFFFFFFFFB7')
    # d = f.decode_payload()
    # assert d == b'\x01@ \xe8\x95\x02\xcf0\xff|\xff\xffr\x00\x0f\xff\xff\xff\xff\xe8\x95\x02\xcf0\xff|\xff\xffr\x00\x0f\xff\xff\xff\xff\xb7'

    radio = io.Radio()
    print(repr(radio.get_model()))
    with Path("data.txt").open("wt") as out:
        mem = radio.clone_from(out)
    with Path("mem.txt").open("wt") as out:
        for line in mem.dump():
            out.write(line)
            out.write("\n")


def main2() -> None:
    mem = model.RadioMemory()
    with Path("mem.txt").open("rt") as inp:
        for line in inp:
            mem.read(line.strip())

    with Path("mem2.txt").open("wt") as out:
        for line in mem.dump():
            out.write(line)
            out.write("\n")


def main() -> None:
    mem = io.load_icf_file(Path("mem.txt"))

    print("channels")
    for channel in range(1300):
        print(channel, mem.get_channel(channel))

    print("banks")
    for idx in range(22):
        print(idx, mem.get_bank(idx))

    print("scan links")
    for idx in range(10):
        print(idx, mem.get_scan_link(idx))

    print("scan edges")
    for idx in range(25):
        print(idx, mem.get_scan_edge(idx))

    # io.save_raw_memory(Path("mem.raw"), mem)


def main_gui() -> None:
    gui.start_gui()

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
import typing as ty
from pathlib import Path
import binascii

from . import gui, io

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
    io.save_icf_file(Path(sys.argv[3]), radio.clone_from())


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
        ch = mem.channels[channel]
        if not ch.hide_channel or not ch.freq or hidden:
            print(channel, ch)


def main_print_channels_4test() -> None:
    """cmd: channels4t
    args: <icf file>"""
    if len(sys.argv) < 3:
        print("file name required")
        return

    mem = io.load_icf_file(Path(sys.argv[2]))

    hidden = False
    ch_start, ch_end = 0, 1300
    for channel in range(ch_start, ch_end):
        ch = mem.channels[channel]
        if not ch.hide_channel or not ch.freq or hidden:
            assert ch.debug_info
            print(
                f"({ch.freq}, {ch.offset}, 0b{ch.freq_flags:04b}, "
                f"{ch.debug_info['offset']})"
            )


def main_print_aw_channels() -> None:
    """cmd: autowrite
    args: <icf file>
    """
    if len(sys.argv) < 3:
        print("file name required")
        return

    mem = io.load_icf_file(Path(sys.argv[2]))

    print("Autowrite channels")
    for channel in mem.awchannels:
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
    for idx, bank in enumerate(mem.banks):
        print(idx, bank, mem.get_bank_channels(idx))


def main_print_scan_programs() -> None:
    """cmd: scan
    args: <icf file>
    """
    if len(sys.argv) < 3:
        print("file name required")
        return

    mem = io.load_icf_file(Path(sys.argv[2]))

    print("Scan links")
    for idx, sl in enumerate(mem.scan_links):
        print(idx, sl)

    print("Scan edges")
    for idx, se in enumerate(mem.scan_edges):
        print(idx, se)


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
    sett = mem.settings
    print(repr(sett))

    print("Bank links")
    bl = mem.bank_links
    print(bl)


def main_print_bands() -> None:
    """cmd: bands
    args: <icf file>
    """
    if len(sys.argv) < 3:
        print("file name required")
        return

    mem = io.load_icf_file(Path(sys.argv[2]))

    print("Bands")
    for idx, band in enumerate(mem.bands):
        print(idx, band)


def main_send_command() -> None:
    """cmd: send
    args: <port> <command> <payload>
    """
    if len(sys.argv) < 4:
        print("file name required")
        return

    port = sys.argv[2]
    cmd = int(sys.argv[3], 16)
    payload = binascii.unhexlify(sys.argv[4]) if len(sys.argv) > 4 else b""

    r = io.Radio(port)
    print("Response: ")
    try:
        for res in r.write_read(cmd, payload):
            print(binascii.hexlify(res.payload))

    except KeyboardInterrupt:
        pass

    except io.NoDataError:
        print("no more data")


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
    print(f"{sys.argv[0]} <command>\nCommand:")

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
            main_print_bands,
            main_send_command,
            # debug, for tests
            main_print_channels_4test,
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

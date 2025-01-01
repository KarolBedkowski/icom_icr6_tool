#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
# ruff: noqa: PLR2004

""" """

import argparse
import binascii
import csv
import logging
import sys
import typing as ty
from pathlib import Path

from . import expimp, io, model

_LOG = logging.getLogger()


def _print_csv(
    data: ty.Iterable[dict[str, object]], columns: ty.Sequence[str]
) -> None:
    writer = csv.DictWriter(
        sys.stdout,
        fieldnames=columns,
        quoting=csv.QUOTE_NONNUMERIC,
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(data)


def main_clone_from_radio(args: argparse.Namespace) -> None:
    """cmd: clone_from_radio
    args: <port> <icf file>
    """
    radio = io.Radio(args.port)
    io.save_icf_file(args.icf_file, radio.clone_from())
    print(f"Saved {args.icf_file}")


def main_radio_info(args: argparse.Namespace) -> None:
    """cmd: radio_info
    args: <port>
    """
    radio = io.Radio(args.port)
    if model := radio.get_model():
        print(f"Model: {model!r}")
        print(f"Is IC-R6: {model.is_icr6()}")
    else:
        print("ERROR")


def main_print_channels(args: argparse.Namespace) -> None:
    """cmd: channels
    args: <icf file> [<start channel num>] [hidden]"""
    mem = io.load_icf_file(args.icf_file)

    ch_start, ch_end = 0, 1300
    if (gr := args.group) is not None and 0 <= gr <= 12:
        ch_start = gr * 100
        ch_end = ch_start + 100

    print("Channels")
    channels = (mem.channels[c] for c in range(ch_start, ch_end))
    if not args.hidden:
        channels = (chan for chan in channels if not chan.hide_channel)

    if args.verbose > 2:
        for ch in channels:
            print(ch)
    else:
        _print_csv(
            (ch.to_record() for ch in channels), expimp.CHANNEL_FIELDS_W_BANKS
        )


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


def main_print_aw_channels(args: argparse.Namespace) -> None:
    """cmd: autowrite
    args: <icf file>
    """
    mem = io.load_icf_file(args.icf_file)

    print("Autowrite channels")
    if args.verbose > 2:
        for ch in mem.awchannels:
            print(ch)
    else:
        _print_csv(
            (ch.to_record() for ch in mem.awchannels),
            expimp.AWCHANNEL_FIELDS,
        )


def main_print_banks(args: argparse.Namespace) -> None:
    """cmd: banks
    args: <icf file>
    """
    mem = io.load_icf_file(args.icf_file)

    print("Banks")
    if args.verbose > 2:
        for bank in mem.banks:
            print(bank, mem.get_bank_channels(bank.idx))
    else:
        data = (
            {
                "bank": b.idx,
                "name": b.name,
                **{
                    f"pos_{pos}": chan
                    for pos, chan in enumerate(
                        mem.get_bank_channels(b.idx).channels
                    )
                    if chan is not None
                },
            }
            for b in mem.banks
        )
        _print_csv(
            data,
            ["bank", "name", *(f"pos_{i}" for i in range(100))],
        )


def main_print_scan_programs(args: argparse.Namespace) -> None:
    """cmd: scan
    args: <icf file>
    """
    mem = io.load_icf_file(args.icf_file)

    print("Scan links")
    if args.verbose > 2:
        for idx, sl in enumerate(mem.scan_links):
            print(idx, sl)
    else:
        data = (
            {
                "scan_link": sl.idx,
                "name": sl.name,
                **{
                    f"scan_edge_{pos}": str(se)
                    for pos, se in enumerate(sl.links())
                    if se
                },
            }
            for sl in mem.scan_links
        )
        _print_csv(
            data,
            ["scan_link", "name", *(f"scan_edge_{i}" for i in range(25))],
        )

    print()
    print("Scan edges")
    if args.verbose > 2:
        for idx, se in enumerate(mem.scan_edges):
            print(idx, se)
    else:
        _print_csv(
            (se.to_record() for se in mem.scan_edges), expimp.SCAN_EDGE_FIELDS
        )


def main_write_mem_raw(args: argparse.Namespace) -> None:
    """cmd: icf2raw
    args: <icf file> [<raw file>]
    """
    mem = io.load_icf_file(args.icf_file)
    dst = args.raw_file or args.icf_file.with_suffix(".raw")
    io.save_raw_memory(dst, mem)
    print(f"Saved {dst}")


def main_write_icf_mem(args: argparse.Namespace) -> None:
    """cmd: raw2icf
    args: <raw file> [<icf file>]
    """

    mem = io.load_raw_memory(args.raw_file)
    dst = args.icf_file or args.raw_file.with_suffix(".icf")
    io.save_icf_file(dst, mem)
    print(f"Saved {dst}")


def main_print_settings(args: argparse.Namespace) -> None:
    """cmd: settings
    args: <icf file>
    """
    mem = io.load_icf_file(args.icf_file)

    print("Settings")
    if args.verbose > 2:
        sett = mem.settings
        print(repr(sett))
    else:
        for key, val in mem.settings.values():
            print(key, val, sep=",")

    print()
    print("Bank links")
    if args.verbose > 2:
        print(mem.bank_links)
    else:
        print(mem.bank_links.human())


def main_print_bands(args: argparse.Namespace) -> None:
    """cmd: bands
    args: <icf file>
    """
    mem = io.load_icf_file(args.icf_file)

    print("Bands")
    if args.verbose > 2:
        for band in mem.bands:
            print(band)
    else:
        _print_csv((b.to_record() for b in mem.bands), expimp.BANDS_FIELDS)


def main_print_dupl_freq(args: argparse.Namespace) -> None:
    """cmd: duplicated-freq
    args: <icf file>
    """
    mem = io.load_icf_file(args.icf_file)

    print("Duplicated channels by frequency")

    freq_channels = sorted(mem.find_duplicated_channels_freq(args.precision))
    if not freq_channels:
        print("no duplicates")
        return

    if args.verbose > 2:
        for freq, num, channels in freq_channels:
            print(freq, "channels:", num)
            for ch in channels:
                print(ch)

            print()

    else:
        data = []
        for freq, num, channels in freq_channels:
            for ch in channels:
                rec = ch.to_record()
                rec["dupl_freq"] = freq
                rec["dupl_channels"] = num
                data.append(rec)

        _print_csv(
            data,
            ["dupl_freq", "dupl_channels", *expimp.CHANNEL_FIELDS_W_BANKS],
        )


def main_send_command(args: argparse.Namespace) -> None:
    """cmd: send
    args: <port> <command> <payload>
    """
    cmd = int(args.command, 16)
    payload = binascii.unhexlify(args.payload) if args.payload else b""

    r = io.Radio(args.port)
    print("Response: ")
    try:
        for res in r.write_read(cmd, payload):
            print(repr(res))

    except KeyboardInterrupt:
        pass

    except io.NoDataError:
        print("no more data")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        help="increase log level",
        default=0,
    )

    cmds = parser.add_subparsers(required=True)

    cmd = cmds.add_parser(
        "clone_from_radio", help="Clone memory from radio into ICF file"
    )
    cmd.add_argument("port", help="USB/TTY/COM port")
    cmd.add_argument("icf_file", type=Path, help="Input ICF file")
    cmd.set_defaults(func=main_clone_from_radio)

    cmd = cmds.add_parser("radio_info", help="Get information about radio")
    cmd.add_argument("port", help="USB/TTY/COM port")
    cmd.set_defaults(func=main_radio_info)

    cmd = cmds.add_parser("channels", help="Print channels")
    cmd.add_argument("icf_file", type=Path, help="Input ICF file")
    cmd.add_argument(
        "-g",
        "--group",
        type=int,
        help="show channels only in one group (0-12)",
    )
    cmd.add_argument("-H", "--hidden", type=int, help="Show hidden channels")
    cmd.set_defaults(func=main_print_channels)

    cmd = cmds.add_parser("awchannels", help="Print autowrite channels")
    cmd.add_argument("icf_file", type=Path, help="Input ICF file")
    cmd.set_defaults(func=main_print_aw_channels)

    cmd = cmds.add_parser("banks", help="Print banks")
    cmd.add_argument("icf_file", type=Path, help="Input ICF file")
    cmd.set_defaults(func=main_print_banks)

    cmd = cmds.add_parser("scan", help="Print scan programs")
    cmd.add_argument("icf_file", type=Path, help="Input ICF file")
    cmd.set_defaults(func=main_print_scan_programs)

    cmd = cmds.add_parser(
        "icf2raw", help="Convert ICF file to raw memory file"
    )
    cmd.add_argument("icf_file", type=Path, help="Input ICF file")
    cmd.add_argument("raw_file", type=Path, nargs="?", help="output raw file")
    cmd.set_defaults(func=main_write_mem_raw)

    cmd = cmds.add_parser(
        "raw2icf", help="Convert raw memory file into ICF file"
    )
    cmd.add_argument("raw_file", type=Path, help="Input raw file")
    cmd.add_argument("icf_file", type=Path, nargs="?", help="output ICF file")
    cmd.set_defaults(func=main_write_icf_mem)

    cmd = cmds.add_parser("settings", help="Print radio settings")
    cmd.add_argument("icf_file", type=Path, help="Input ICF file")
    cmd.set_defaults(func=main_print_settings)

    cmd = cmds.add_parser("bands", help="Print default bands configuration")
    cmd.add_argument("icf_file", type=Path, help="Input ICF file")
    cmd.set_defaults(func=main_print_bands)

    cmd = cmds.add_parser(
        "duplicated-freq", help="Print duplicated channels by frequency"
    )
    cmd.add_argument("icf_file", type=Path, help="Input ICF file")
    cmd.add_argument(
        "--precision",
        type=int,
        default=3,
        help="Skip given number of less significant digits",
    )
    cmd.set_defaults(func=main_print_dupl_freq)

    cmd = cmds.add_parser("send", help="Send command to radio")
    cmd.add_argument("port", help="USB/TTY/COM port")
    cmd.add_argument("command", help="Command to send (1 byte in hex)")
    cmd.add_argument(
        "payload", help="Payload to send in hex string", nargs="?"
    )
    cmd.set_defaults(func=main_send_command)

    return parser.parse_args()


def main() -> None:
    logging.basicConfig()

    args = _parse_args()

    match args.verbose:
        case 0:
            logging.getLogger().setLevel(logging.WARNING)
        case 1:
            logging.getLogger().setLevel(logging.INFO)
        case _:
            logging.getLogger().setLevel(logging.DEBUG)
            model.enable_debug()

    args.func(args)

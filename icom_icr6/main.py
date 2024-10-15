#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import binascii
import logging
import struct
import typing as ty
from collections import abc
from dataclasses import dataclass
from pathlib import Path

import icecream
import serial

icecream.install()

ic = icecream.ic

ADDR_PC = 0xEE
ADDR_RADIO = 0x7E
LOG = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG)


@dataclass
class Frame:
    cmd: int = 0
    payload: bytes = b""

    def pack(self) -> bytes:
        return b"".join(
            (
                b"\xfe\xfe",
                struct.pack("BBB", ADDR_PC, ADDR_RADIO, self.cmd),
                self.payload,
                b"\xfd",
            )
        )

    def decode_payload(self) -> bytes:
        # print("in", repr(self.payload))
        res = b"".join(
            struct.pack("B", int(self.payload[i : i + 2], 16))
            for i in range(0, len(self.payload) - 1, 2)
        )

        # print("out", repr(res))
        return res


@dataclass
class RadioModel:
    rev: int
    comment: bytes


TONE_MODES = ["", "TSQL", "TSQL-R", "DTCS", "DTCS-R", "", "", ""]
DUPLEX_DIRS = ["", "-", "+"]
MODES = ["FM", "WFM", "AM", "Auto"]
STEPS = [
    5,
    6.25,
    8.333333,
    9,
    10,
    12.5,
    15,
    20,
    25,
    30,
    50,
    100,
    125,
    200,
    "Auto",
]
SKIPS = ["", "S", "", "P"]


@dataclass
class Channel:
    number: int

    freq: int
    freq_flags: int
    af_filter: bool
    attenuator: bool
    mode: int
    tuning_step: int
    duplex: int
    tmode: int
    offset: int
    ctone: int
    canceller_freq: int
    vsc: bool
    canceller: int
    name: str

    # control flags
    hide_channel: bool
    skip: int

    def __str__(self) -> str:
        #ic(self)
        return (
            "Channel {self.number}: "
            f"f={self.freq}, "
            f"ff={self.freq_flags}, "
            f"af={self.af_filter}, "
            f"att={self.attenuator}, "
            f"mode={MODES[self.mode]}, "
            f"ts={self.tuning_step}, "
            f"duplex={self.duplex}, "
            f"tmode={TONE_MODES[self.tmode]}, "
            f"offset={self.offset}, "
            f"ctone={self.ctone}, "
            f"cf={self.canceller_freq}, "
            f"vsc={self.vsc}, "
            f"c={self.canceller}, "
            f"name={self.name!r}, "
            f"hide={self.hide_channel}, "
            f"skip={SKIPS[self.skip]}"
        )


class RadioMemory:
    def __init__(self) -> None:
        self.mem = [0] * 0x6E60

    def update(self, addr: int, length: int, data: bytes) -> None:
        assert len(data) == length
        self.mem[addr : addr + length] = data

    def dump(self, step: int = 16) -> ty.Iterator[str]:
        """Dump data in icf file format."""
        for idx in range(0, 0x6E60, step):
            data = self.mem[idx : idx + step]
            data_hex = binascii.hexlify(bytes(data)).decode()
            res = f"{idx:04x}{step:02x}{data_hex}"
            yield res.upper()

    def read(self, line: str) -> None:
        """Read line from icf file"""
        addr = int(line[0:4], 16)
        size = int(line[4:6], 16)
        data_raw = line[6:]
        assert size * 2 == len(data_raw)
        data = binascii.unhexlify(data_raw)
        self.mem[addr : addr + size] = data

    def get_channel(self, idx: int) -> Channel:
        start = idx * 16
        data = self.mem[start : start + 16]
        #ic(data)
        freq = ((data[2] & 0b00000011) << 16) | (data[1] << 8) | data[0]
        freq_flags = (data[2] & 0b11111100) >> 2

        cflags_start = idx * 2 + 0x5F80
        cflags = self.mem[cflags_start : cflags_start + 1]

        return Channel(
            number=idx,
            freq=decode_freq(freq, freq_flags),
            freq_flags=freq_flags,
            af_filter=bool(data[3] & 0b10000000),
            attenuator=bool(data[3] & 0b01000000),
            mode=(data[3] & 0b00110000) >> 4,
            tuning_step=data[3] & 0b00001111,
            duplex=(data[4] & 0b11000000) >> 6,
            tmode=data[4] & 0b00000111,
            offset=decode_freq((data[6] << 8) | data[5], freq_flags),
            ctone=int(data[7]) & 0b00111111,
            canceller_freq=(data[9] << 1) | ((data[10] & 0b10000000) >> 7),
            vsc=bool(data[10] & 0b00000100),
            canceller=bool(data[10] & 0b00000011),
            name=decode_name(data[11:16]),
            hide_channel=bool(cflags[0] & 0b10000000),
            skip=(cflags[0] & 0b01100000) >> 5,
        )


CODED_CHRS = " ^^^^^^^()*+^-./0123456789:^^=^^^ABCDEFGHIJKLMNOPQRSTUVWXYZ^^^^^"


def decode_name(inp: list[int]) -> str:
    chars = (
        (inp[0] & 0b00001111) << 2 | (inp[1] & 0b11000000) >> 6,
        (inp[1] & 0b00111111),
        (inp[2] & 0b11111100) >> 2,
        (inp[2] & 0b00000011) << 4 | (inp[3] & 0b11110000) >> 4,
        (inp[3] & 0b00001111) << 2 | (inp[4] & 0b11000000) >> 6,
        (inp[4] & 0b00111111),
    )

    return "".join(CODED_CHRS[x] for x in chars)


def decode_freq(freq: int, flags: int) -> int:
    match flags:
        case 0:
            return 5000 * freq
        case 20:
            return 6250 * freq
        case 40:
            return int(8333.3333 * freq)
        case 60:
            return 9000 * freq

    raise ValueError(f"unknown flag {flag!r} for freq {freq}")


class Radio:
    def __init__(self) -> None:
        self.ser = serial.Serial("/dev/ttyUSB1", 9600)

    def _write(self, payload: bytes) -> None:
        LOG.debug("write: %s", binascii.hexlify(payload))
        self.ser.write(payload)

    def read_frame(self) -> Frame | None:
        buf: list[bytes] = []

        while True:
            if d := self.ser.read(1):
                buf.append(d)
                if d != b"\xfd":
                    continue
            else:
                LOG.error("no data")
                break

            data = b"".join(buf)

            if not data:
                return None

            if not data.startswith(b"\xfe\xfe"):
                LOG.error("frame out of sync: %r", data)
                raise ValueError("out of sync")

            if len(data) < 5:
                continue

            # ic(data, len(data))
            while data.startswith(b"\xfe\xfe\xfe"):
                LOG.debug("remove prefix")
                data = data[1:]

            if len(data) < 5:
                continue

            if data[2] == ADDR_PC and data[3] == ADDR_RADIO:
                LOG.debug("got echo")
                buf.clear()
                continue

            # ic(data)
            return Frame(data[4], data[5:])

        return None

    def get_model(self) -> RadioModel | None:
        self._write(Frame(0xE0, b"\x00\x00\x00\x00").pack())
        if frame := self.read_frame():
            LOG.debug("%d: %r", len(frame.payload), frame)
            pl = frame.payload
            return RadioModel(pl[5], pl[6:22])

        return None

    def clone_from(self, out: ty.TextIO) -> RadioMemory:
        self._write(Frame(0xE2, b"\x32\x50\x00\x01").pack())
        mem = RadioMemory()
        while True:
            if frame := self.read_frame():
                LOG.debug("read: %r", frame)
                match int(frame.cmd):
                    case 0xE5:  # clone_end
                        break

                    case 0xE4:  # clone_dat
                        data = frame.decode_payload()
                        # LOG.debug("decoded: %s", binascii.hexlify(data))
                        (daddr,) = struct.unpack(">H", data[0:2])
                        (length,) = struct.unpack("B", data[2:3])
                        # TODO: checksum?
                        mem.update(daddr, length, data[3 : 3 + length])
                        out.write(f"{frame.payload[:-2].decode()}\n")

                    case _:
                        raise ValueError

        return mem


def main1() -> None:
    # f = Frame(0, b'014020E89502CF30FF7CFFFF72000FFFFFFFFFE89502CF30FF7CFFFF72000FFFFFFFFFB7')
    # d = f.decode_payload()
    # assert d == b'\x01@ \xe8\x95\x02\xcf0\xff|\xff\xffr\x00\x0f\xff\xff\xff\xff\xe8\x95\x02\xcf0\xff|\xff\xffr\x00\x0f\xff\xff\xff\xff\xb7'

    radio = Radio()
    print(repr(radio.get_model()))
    with Path("data.txt").open("wt") as out:
        mem = radio.clone_from(out)
    with Path("mem.txt").open("wt") as out:
        for line in mem.dump():
            out.write(line)
            out.write("\n")


def main2() -> None:
    mem = RadioMemory()
    with Path("mem.txt").open("rt") as inp:
        for line in inp:
            mem.read(line.strip())

    with Path("mem2.txt").open("wt") as out:
        for line in mem.dump():
            out.write(line)
            out.write("\n")


def main() -> None:
    mem = RadioMemory()
    with Path("mem.txt").open("rt") as inp:
        for line in inp:
            mem.read(line.strip())

    for channel in range(500, 600):  # 1300):
        print(channel, mem.get_channel(channel))

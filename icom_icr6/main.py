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
        print("in", repr(self.payload))
        res = b"".join(
            struct.pack("B", int(self.payload[i : i + 2], 16))
            for i in range(0, len(self.payload) - 1, 2)
        )

        print("out", repr(res))
        return res


@dataclass
class RadioModel:
    rev: int
    comment: bytes


class Radio:
    def __init__(self) -> None:
        self.ser = serial.Serial("/dev/ttyUSB1", 9600)

    def _write(self, payload: bytes) -> None:
        LOG.debug("write: %s", binascii.hexlify(payload))
        self.ser.write(payload)

    def read_frame(self) -> Frame | None:
        buf : list[bytes]= []

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

            if not data.startswith(b"\xFE\xFE"):
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

    def get_model(self) -> RadioModel:
        self._write(Frame(0xE0, b"\x00\x00\x00\x00").pack())
        frame = self.read_frame()
        LOG.debug("%d: %r", len(frame.payload), frame)
        pl = frame.payload
        return RadioModel(pl[5], pl[6:22])

    def clone_from(self, out: ty.TextIO) -> list[int]:
        self._write(Frame(0xE2, b"\x32\x50\x00\x01").pack())
        mem = [0] * 0x6E60
        addr = 0
        while True:
            if frame := self.read_frame():
                LOG.debug("read: %r", frame.payload)
                match int(frame.cmd):
                    case 0xE5:  # clone_end
                        mem = mem[:addr]
                        break

                    case 0xE4:  # clone_dat
                        data = frame.decode_payload()
                        LOG.debug("decoded: %s", binascii.hexlify(data))
                        (daddr,) = struct.unpack(">H", data[0:2])
                        (length,) = struct.unpack("B", data[2:3])
                        #ic(daddr, length, data[3 : 3 + length], data)
                        real_data = data[3 : 3 + length]
                        mem[daddr : daddr + length] = real_data
                        #out.write(f"{daddr} {length} {real_data!r}\n")
                        out.write(f"{frame.payload[:-2].decode()}\n")
                        #out.write(binascii.hexlify(real_data).decode())
                        #out.write("\n")
                        addr = daddr + length

                    case _:
                        raise ValueError

        return mem


def main() -> None:

    # f = Frame(0, b'014020E89502CF30FF7CFFFF72000FFFFFFFFFE89502CF30FF7CFFFF72000FFFFFFFFFB7')
    # d = f.decode_payload()
    # assert d == b'\x01@ \xe8\x95\x02\xcf0\xff|\xff\xffr\x00\x0f\xff\xff\xff\xff\xe8\x95\x02\xcf0\xff|\xff\xffr\x00\x0f\xff\xff\xff\xff\xb7'

    radio = Radio()
    print(repr(radio.get_model()))
    with Path("data.txt").open("wt") as out:
        radio.clone_from(out)

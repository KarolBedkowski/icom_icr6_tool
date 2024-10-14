#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

"""

"""
from dataclasses import dataclass
import struct
import logging
import binascii
import typing as ty

import serial
import icecream
icecream.install()

ADDR_PC = 0xEE
ADDR_RADIO = 0x7E
LOG = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG)


@dataclass
class Frame:
    cmd: str = ""
    payload: bytes = b""

    def pack(self) -> bytes:
        return b''.join((b'\xfe\xfe',
                struct.pack('BBB', ADDR_PC, ADDR_RADIO, self.cmd),
                self.payload, b'\xfd'))


@dataclass
class RadioModel:
    rev: str
    comment: str


class Radio:
    def __init__(self) -> None:
        self.ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=5)

    def read_frames(self) -> ty.Iterator[Frame]:
        buf : bytes = []

        while len(buf) < 1024:
            if d := self.ser.read(1):
                buf.append(d)
            else:
                break

        data = b''.join(buf)
        ic(data, len(data))

        if not data:
            return

        if not data.startswith(b"\xFE\xFE") or len(data) < 5:
            raise ValueError("invalid frame")

        while data:
            ic(data, len(data))
            while data.startswith(b'\xfe\xfe\xfe'):
                data = data[1:]

            if len(data) < 4:
                raise ValueError

            end = data.index(b'\xFD')
            if data[2] != ADDR_PC or data[3] != ADDR_RADIO:
                yield Frame(data[4], data[5:end])

            data = data[end+1:]


    def get_model(self) -> RadioModel:
        frame = Frame(0xe0, b"\x00\x00\x00\x00")
        self.ser.write(ic(frame.pack()))
        frames = list(self.read_frames())
        LOG.debug("%r", frames)
        pl = frames[0].payload
        return RadioModel(pl[5], pl[6:22])




radio = Radio()
print(radio.get_model())

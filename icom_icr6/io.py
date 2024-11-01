# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import binascii
import itertools
import logging
import struct
from dataclasses import dataclass
from pathlib import Path

import serial

from . import model

ADDR_PC = 0xEE
ADDR_RADIO = 0x7E

_LOG = logging.getLogger(__name__)


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
        return b"".join(
            struct.pack("B", int(self.payload[i : i + 2], 16))
            for i in range(0, len(self.payload) - 1, 2)
        )


class OutOfSyncError(ValueError): ...


class Radio:
    def __init__(self) -> None:
        self.ser = serial.Serial("/dev/ttyUSB0", 9600)

    def _write(self, payload: bytes) -> None:
        _LOG.debug("write: %s", binascii.hexlify(payload))
        self.ser.write(payload)

    def read_frame(self) -> Frame | None:
        buf: list[bytes] = []

        while True:
            if d := self.ser.read(1):
                buf.append(d)
                if d != b"\xfd":
                    continue
            else:
                _LOG.error("no data")
                break

            if not buf:
                return None

            data = b"".join(buf)

            if not data.startswith(b"\xfe\xfe"):
                _LOG.error("frame out of sync: %r", data)
                raise OutOfSyncError

            # ic(data, len(data))
            while data.startswith(b"\xfe\xfe\xfe"):
                _LOG.debug("remove prefix")
                data = data[1:]

            if len(data) < 5:  # noqa: PLR2004
                continue

            if data[2] == ADDR_PC and data[3] == ADDR_RADIO:
                _LOG.debug("got echo")
                buf.clear()
                continue

            # ic(data)
            return Frame(data[4], data[5:])

        return None

    def get_model(self) -> model.RadioModel | None:
        self._write(Frame(0xE0, b"\x00\x00\x00\x00").pack())
        if frame := self.read_frame():
            _LOG.debug("%d: %r", len(frame.payload), frame)
            pl = frame.payload
            return model.RadioModel(pl[5], pl[6:22])

        return None

    def clone_from(self) -> model.RadioMemory:
        self._write(Frame(0xE2, b"\x32\x50\x00\x01").pack())
        mem = model.RadioMemory()
        for idx in itertools.count():
            if frame := self.read_frame():
                _LOG.debug("read: %d: %r", idx, frame)
                match int(frame.cmd):
                    case 0xE5:  # clone_end
                        break

                    case 0xE4:  # clone_dat
                        rawdata = frame.decode_payload()
                        # _LOG.debug("decoded: %s", binascii.hexlify(data))
                        addr1, addr2, daddr, length = struct.unpack(
                            "BB>HB", rawdata[0:3]
                        )
                        data = rawdata[3 : 3 + length]
                        # checksum?
                        (checksum,) = struct.unpack("B", rawdata[3 + length :])
                        calc_checksum = addr1 + addr2 + length + sum(data)
                        calc_checksum = ((checksum ^ 0xFFFF) + 1) & 0xFF

                        if checksum != calc_checksum:
                            _LOG.error(
                                "invalid checksum: idx=%d, exp=%d, rec=%d, "
                                "frame=%s",
                                idx,
                                calc_checksum,
                                checksum,
                                binascii.hexlify(data),
                            )
                            raise ChecksumError

                        mem.update(daddr, length, data)
                        # out.write(f"{frame.payload[:-2].decode()}\n")

                    case _:
                        _LOG.error(
                            "unknown cmd=%r idx=%d frame=%s",
                            frame.cmd, idx,
                            binascii.hexlify(data),
                        )
                        raise ValueError

        return mem


class ChecksumError(Exception):
    pass


class InvalidFileError(Exception):
    pass


def load_icf_file(file: Path) -> model.RadioMemory:
    """Load icf file as RadioMemory."""
    mem = model.RadioMemory()

    with file.open("rt") as inp:
        try:
            if next(inp).strip() != "32500001":
                raise InvalidFileError
        except StopIteration as exc:
            raise InvalidFileError from exc

        for line in inp:
            if line.startswith("#"):
                continue

            if line := line.strip():
                mem.read(line)

    return mem


def save_icf_file(file: Path, mem: model.RadioMemory) -> None:
    """Write RadioMemory to icf file."""
    with file.open("wt") as out:
        # header
        out.write("32500001\r\n#Comment=\r\n#MapRev=1\n#EtcData=001A\r\n")
        # data
        for line in mem.dump():
            out.write(line)
            out.write("\r\n")


def save_raw_memory(file: Path, mem: model.RadioMemory) -> None:
    """Write RadioMemory to binary file."""
    with file.open("wb") as out:
        out.write(bytes(mem.mem))

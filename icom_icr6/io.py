# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import binascii
import itertools
import logging
import struct
import typing as ty
from dataclasses import dataclass
from pathlib import Path

import serial

from . import consts, model

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
                bytes([0xFE, 0xFE, ADDR_PC, ADDR_RADIO, self.cmd]),
                self.payload,
                b"\xfd",
            )
        )

    def decode_payload(self) -> bytes:
        # print("in", repr(self.payload))
        return bytes(
            int(self.payload[i : i + 2], 16)
            for i in range(0, len(self.payload) - 1, 2)
        )


class OutOfSyncError(ValueError): ...


class RealSerial:
    def __init__(self, port: str = "") -> None:
        self.port = port

    def open(self, _stream: str = "") -> None:
        self._serial = serial.Serial(self.port or "/dev/ttyUSB0", 9600)
        self._serial.timeout = 5
        self._serial.write_timeout = 5

    def close(self) -> None:
        self._serial.close()

    def write(self, data: bytes) -> None:
        self._serial.write(data)

    def read(self, length: int) -> bytes:
        return self._serial.read(length)  # type: ignore


class FakeSerial:
    def __init__(self, _port: str = "") -> None:
        self._file_in = None
        self._file_out = None

    def open(self, stream: str = "") -> None:
        self._file_in = Path(f"{stream}-in.bin").open("rb")  # noqa: SIM115
        self._file_out = Path(f"{stream}-out.bin").open("wb")  # noqa: SIM115

    def close(self) -> None:
        if self._file_in:
            self._file_in.close()

        if self._file_out:
            self._file_out.close()

    def write(self, data: bytes) -> None:
        assert self._file_out
        self._file_out.write(data)

    def read(self, length: int) -> bytes:
        assert self._file_in
        return self._file_in.read(length)


def calc_checksum(data: bytes) -> int:
    return ((sum(data) ^ 0xFFFF) + 1) & 0xFF


class Radio:
    def __init__(self, port: str = "") -> None:
        self._serial = FakeSerial(port)
        self._logger = None
        self._stream_logger = None
        self._stream_logger = Path("data.log").open("wt")

    def _write(self, payload: bytes) -> None:
        pl = binascii.hexlify(payload)
        _LOG.debug("write: %s", pl)
        self._serial.write(payload)
        if self._stream_logger:
            self._stream_logger.write(f"<{pl!r}\n")

    def read_frame(self) -> Frame | None:
        buf: list[bytes] = []

        while True:
            if d := self._serial.read(1):
                buf.append(d)
                if d != b"\xfd":
                    continue
            else:
                _LOG.error("no data")
                raise NoDataError

            data = b"".join(buf)
            if self._stream_logger:
                self._stream_logger.write(f">{binascii.hexlify(data)!r}\n")

            if not data or data == b"\xfd":
                return None

            if not data.startswith(b"\xfe\xfe"):
                _LOG.error("frame out of sync: %r", data)
                raise OutOfSyncError

            if len(data) < 5:  # noqa: PLR2004
                continue

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

    def _process_clone_from_frame(
        self, idx: int, frame: Frame, mem: model.RadioMemory
    ) -> bool:
        match int(frame.cmd):
            case 0xE5:  # clone_end
                return False

            case 0xE4:  # clone_dat
                rawdata = frame.decode_payload()
                # _LOG.debug("decoded: %s", binascii.hexlify(data))
                daddr = (rawdata[0] << 8) | rawdata[1]
                length = rawdata[2]
                data = rawdata[3 : 3 + length]
                # checksum?
                checksum = rawdata[3 + length]
                my_checksum = calc_checksum(rawdata[: length + 3])

                if checksum != my_checksum:
                    _LOG.error(
                        "invalid checksum: idx=%d, exp=%d, rec=%d, "
                        "frame=%s",
                        idx,
                        calc_checksum,
                        checksum,
                        binascii.hexlify(rawdata),
                    )
                    self._serial.close()
                    raise ChecksumError

                mem.update(daddr, length, data)
                # out.write(f"{frame.payload[:-2].decode()}\n")
            case _:
                _LOG.error(
                    "unknown cmd=%r idx=%d frame=%s",
                    frame.cmd,
                    idx,
                    binascii.hexlify(frame.payload),
                )
                self._serial.close()
                raise ValueError

        return True

    def clone_from(
        self, cb: ty.Callable[[int], bool] | None = None
    ) -> model.RadioMemory:
        self._serial.open("clone_from")
        # clone out
        self._write(Frame(0xE2, b"\x32\x50\x00\x01").pack())
        mem = model.RadioMemory()
        for idx in itertools.count():
            if frame := self.read_frame():
                _LOG.debug("read: %d: %r", idx, frame)

                if not self._process_clone_from_frame(idx, frame, mem):
                    break

                if cb and not cb(idx):
                    self._serial.close()
                    raise AbortError

        # self._logger.close()
        self._serial.close()
        return mem


class NoDataError(Exception):
    def __str__(self) -> str:
        return "Communication error"


class ChecksumError(Exception):
    def __str__(self) -> str:
        return "Checksum error"


class AbortError(Exception):
    def __str__(self) -> str:
        return "Aborted"


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

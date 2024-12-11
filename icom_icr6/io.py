# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import binascii
import itertools
import logging
import time
import typing as ty
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import serial

from . import consts, model
from .radio_memory import RadioMemory

ADDR_PC: ty.Final = 0xEE
# TODO: configurable
ADDR_RADIO: ty.Final = 0x7E
CMD_MODEL: ty.Final = 0xE0  # todo: check - 0xE1?
CMD_CLONE_OUT: ty.Final = 0xE2
CMD_CLONE_IN: ty.Final = 0xE3
CMD_CLONE_DAT: ty.Final = 0xE4
CMD_CLONE_HISPEED: ty.Final = 0xE8
CMD_END: ty.Final = 0xE5
CMD_OK: ty.Final = 0xE6


_LOG = logging.getLogger(__name__)

# log input/output data
_ENABLE_LOGGER = False


@dataclass
class Frame:
    cmd: int = 0
    payload: bytes = b""
    src: int = ADDR_PC
    dst: int = ADDR_RADIO

    def pack(self) -> bytes:
        return b"".join(
            (
                bytes([0xFE, 0xFE, self.src, self.dst, self.cmd]),
                self.payload,
                b"\xfd",
            )
        )

    def decode_payload(self) -> bytes:
        return bytes(
            int(self.payload[i : i + 2], 16)
            for i in range(0, len(self.payload) - 1, 2)
        )

    def is_echo(self) -> bool:
        return self.src == ADDR_PC and self.dst == ADDR_RADIO


@ty.runtime_checkable
class Serial(ty.Protocol):
    def write(self, data: bytes) -> None: ...

    def read(self, length: int) -> bytes: ...

    def read_frame(self) -> bytes: ...

    def open(self, stream: str) -> None: ...

    def close(self) -> None: ...

    def switch_to_hispeed(self) -> None: ...


class StreamLogger:
    """
    StreamLogger wrape Serial and append output/input to data.log file.
    """

    def __init__(self, impl: Serial) -> None:
        self._impl = impl
        self._log = Path("data.log").open("at")  # noqa: SIM115

    def open(self, stream: str) -> None:
        self._impl.open(stream)

    def close(self) -> None:
        self._impl.close()
        self._log.close()

    def write(self, data: bytes) -> None:
        self._log.write(f"<{binascii.hexlify(data)!r}\n")
        self._impl.write(data)

    def read(self, length: int) -> bytes:
        data = self._impl.read(length)
        self._log.write(f">{binascii.hexlify(data)!r}\n")
        return data

    def read_frame(self) -> bytes:
        data = self._impl.read_frame()
        self._log.write(f">{binascii.hexlify(data)!r}\n")
        return data

    def switch_to_hispeed(self) -> None:
        self._impl.switch_to_hispeed()


class RealSerial:
    def __init__(self, port: str) -> None:
        self.port = port

    def open(self, _stream: str) -> None:
        _LOG.info("opening serial %r", self.port)
        self._serial = serial.Serial(self.port or "/dev/ttyUSB0", 9600)
        self._serial.timeout = 5
        self._serial.write_timeout = 5

    def close(self) -> None:
        _LOG.info("closing serial")
        self._serial.close()

    def write(self, data: bytes) -> None:
        assert self._serial
        self._serial.write(data)

    def read(self, length: int) -> bytes:
        assert self._serial
        return self._serial.read(length)  # type: ignore

    def read_frame(self) -> bytes:
        buf: list[bytes] = []
        while d := self._serial.read(1):
            buf.append(d)
            if d == b"\xfd":
                break

        return b"".join(buf)

    def switch_to_hispeed(self) -> None:
        _LOG.debug("switch_to_hispeed")
        self._serial.flush()
        self._serial.baudrate = 38400


class FakeSerial:
    def open(self, stream: str) -> None:
        _LOG.info("opening files %s", stream)
        self._file_in = Path(f"{stream}-in.bin").open("rb")  # noqa:SIM115
        self._file_out = Path(f"{stream}-out.bin").open("wb")  # noqa:SIM115

    def close(self) -> None:
        _LOG.info("closing files")
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

    def read_frame(self) -> bytes:
        assert self._file_in
        buf: list[bytes] = []
        while d := self._file_in.read(1):
            buf.append(d)
            if d == b"\xfd":
                break

        return b"".join(buf)

    def switch_to_hispeed(self) -> None:
        _LOG.debug("switch_to_hispeed")


def calc_checksum(data: bytes) -> int:
    return ((sum(data) ^ 0xFFFF) + 1) & 0xFF


class Radio:
    def __init__(self, port: str = "") -> None:
        self._port = port
        self._logger = None

    @contextmanager
    def _open_serial(self, stream: str) -> ty.Iterator[Serial]:
        impl: Serial = RealSerial(self._port) if self._port else FakeSerial()

        if _ENABLE_LOGGER:
            impl = StreamLogger(impl)

        impl.open(stream)

        try:
            yield impl
        finally:
            impl.close()

    def _write(self, s: Serial, payload: bytes) -> None:
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("write: %s", binascii.hexlify(payload))

        s.write(payload)

    def read_frame(self, s: Serial) -> Frame | None:
        data = s.read_frame()

        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("read: %s", binascii.hexlify(data))

        if not data:
            _LOG.error("no data")
            raise NoDataError

        if not data or data == b"\xfd":
            return None

        if not data.startswith(b"\xfe\xfe"):
            _LOG.error("frame out of sync: %r", data)
            raise OutOfSyncError

        if len(data) < 5:  # noqa: PLR2004
            return None

        # ic(data, len(data))
        while data.startswith(b"\xfe\xfe\xfe"):
            _LOG.debug("remove prefix")
            data = data[1:]

        if len(data) < 5:  # noqa: PLR2004
            return None

        # ic(data)
        return Frame(data[4], data[5:], data[2], data[3])

    def _start_clone(self, s: Serial, cmd: int, *, hispeed: bool) -> None:
        if not hispeed:
            self._write(s, Frame(cmd, b"\x32\x50\x00\x01").pack())
            return

        self._write(s, b"\xfe" * 20)
        self._write(
            s,
            Frame(
                CMD_CLONE_HISPEED, b"\x32\x50\x00\x01\x00\x00\x02\x01\xfd"
            ).pack(),
        )

        resp = s.read(128)
        _LOG.debug("response: %r", resp)

        s.switch_to_hispeed()

        self._write(s, b"\xfe" * 14)
        self._write(s, Frame(cmd, b"\x32\x50\x00\x00").pack())

    def get_model(self) -> model.RadioModel | None:
        with self._open_serial("get_model") as s:
            self._write(s, Frame(CMD_MODEL, b"\x00\x00\x00\x00").pack())
            while frame := self.read_frame(s):
                if frame.is_echo():
                    continue

                pl = frame.payload
                _LOG.debug("payload: %r", pl)
                return model.RadioModel.from_data(pl)

        return None

    def _process_clone_from_frame(
        self, idx: int, frame: Frame, mem: RadioMemory
    ) -> tuple[bool, int]:
        if frame.is_echo():
            # echo, skip
            return True, 0

        length = 0

        match frame.cmd:
            case 0xE5:  # CMD_END
                return False, 0

            case 0xE4:  # CMD_CLONE_DAT:
                rawdata = frame.decode_payload()
                daddr = (rawdata[0] << 8) | rawdata[1]
                length = rawdata[2]
                data = rawdata[3 : 3 + length]

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
                    raise ChecksumError

                _LOG.debug("update mem: addr=%d, len=%d", daddr, length)
                mem.update_mem_region(daddr, length, data)

            case _:
                _LOG.error(
                    "unknown cmd=%r idx=%d frame=%s",
                    frame.cmd,
                    idx,
                    binascii.hexlify(frame.payload),
                )
                raise ValueError

        return True, length

    def clone_from(
        self, cb: ty.Callable[[int], bool] | None = None
    ) -> RadioMemory:
        self._check_radio()

        total_length = 0

        with self._open_serial("clone_from") as s:
            # clone out
            self._start_clone(s, CMD_CLONE_OUT, hispeed=True)
            # self._write(s, Frame(CMD_CLONE_OUT, b"\x32\x50\x00\x01").pack())

            mem = RadioMemory()
            for idx in itertools.count():
                if frame := self.read_frame(s):
                    _LOG.debug("read: %d: %r", idx, frame)

                    res, length = self._process_clone_from_frame(
                        idx, frame, mem
                    )
                    if not res:
                        break

                    total_length += length
                    if cb and not cb(total_length):
                        raise AbortError

            return mem

    def clone_to(
        self,
        mem: RadioMemory,
        cb: ty.Callable[[int], bool] | None = None,
    ) -> bool:
        self._check_radio()

        time.sleep(1)

        with self._open_serial("clone_to") as s:
            # clone in
            # self._write(s, Frame(CMD_CLONE_IN, b"\x32\x50\x00\x01").pack())
            self._start_clone(s, CMD_CLONE_IN, hispeed=True)

            # send in 32bytes chunks
            for addr in range(0, consts.MEM_SIZE, 32):
                _LOG.debug("process addr: %d", addr)

                chunk = bytes(
                    [(addr >> 8), addr & 0xFF, 32, *mem.mem[addr : addr + 32]]
                )
                # add checksum
                chunk += bytes([calc_checksum(chunk)])
                # encode paload
                payload = "".join(f"{d:02X}" for d in chunk)
                frame = Frame(CMD_CLONE_DAT, payload.encode())

                data = frame.pack()
                if _LOG.isEnabledFor(logging.DEBUG):
                    _LOG.debug("write: %s", binascii.hexlify(data))

                self._write(s, data)

                # TODO: check - get echo
                fr = self.read_frame(s)
                _LOG.debug("read: %r", fr)

                if cb and not cb(addr):
                    raise AbortError

            _LOG.debug("send clone end")
            # clone end
            self._write(s, Frame(CMD_END, b"Icom Inc\x2e73").pack())
            # one more packet?

            result_frame = None
            for i in range(10):
                _LOG.debug("wait for result (%d)", i)
                if result_frame := self.read_frame(s):
                    _LOG.info("got frame: %r", result_frame)
                    if result_frame.cmd == CMD_OK:
                        # clone ok
                        break

            if not result_frame:
                raise NoDataError

            return result_frame.payload[0] == 0

    def _check_radio(self) -> None:
        if not self._port:
            return

        model = self.get_model()
        if not model:
            raise NoDataError

        if not model.is_icr6():
            _LOG.error("unsupported model: %r", model)
            raise UnsupportedDeviceError


class UnsupportedDeviceError(Exception):
    def __str__(self) -> str:
        return "Unsupported device"


class NoDataError(Exception):
    def __str__(self) -> str:
        return "Communication error"


class ChecksumError(Exception):
    def __str__(self) -> str:
        return "Checksum error"


class AbortError(Exception):
    def __str__(self) -> str:
        return "Aborted"


class OutOfSyncError(ValueError):
    def __str__(self) -> str:
        return "Out of sync"


class InvalidFileError(Exception):
    def __str__(self) -> str:
        return "Invalid file"


def _update_from_icf_file(mv: memoryview, line: str) -> None:
    """Read line from icf file"""
    addr = int(line[0:4], 16)
    size = int(line[4:6], 16)
    data_raw = line[6:]
    assert size * 2 == len(data_raw)
    data = binascii.unhexlify(data_raw)
    mv[addr : addr + size] = data


def load_icf_file(file: Path) -> RadioMemory:
    """Load icf file as RadioMemory."""
    _LOG.info("loading %s", file)
    mem = RadioMemory()
    mv = memoryview(mem.mem)

    with file.open("rt") as inp:
        try:
            # check header == model in hex
            if next(inp).strip() != "32500001":
                raise InvalidFileError

        except StopIteration as exc:
            raise InvalidFileError from exc

        for line in inp:
            if line.startswith("#"):
                key, _, val = line.strip()[1:].partition("=")
                match key:
                    case "Comment":
                        mem.file_comment = val
                    case "MapRev":
                        mem.file_maprev = val
                    case "EtcData":
                        mem.file_etcdata = val
                    case _:
                        _LOG.warn("unknown line: %r", line)

                continue

            if line := line.strip():
                _update_from_icf_file(mv, line)

    _LOG.info("loading %s done", file)
    mem.validate()
    mem.load_memory()

    return mem


def load_raw_memory(file: Path) -> RadioMemory:
    mem = RadioMemory()
    with file.open("rb") as inp:
        mem.mem = bytearray(inp.read())

    mem.validate()
    mem.load_memory()
    return mem


def _dump_memory(mem: bytearray, step: int = 16) -> ty.Iterator[str]:
    """Dump data in icf file format."""

    mv = memoryview(mem)
    for idx in range(0, 0x6E60, step):
        data = mv[idx : idx + step]
        data_hex = binascii.hexlify(bytes(data)).decode()
        res = f"{idx:04x}{step:02x}{data_hex}"
        yield res.upper()


def save_icf_file(file: Path, mem: RadioMemory) -> None:
    """Write RadioMemory to icf file."""
    _LOG.info("write %s", file)
    mem.commit()

    with file.open("wt") as out:
        # header
        out.write("32500001\r\n")
        out.write(f"#Comment={mem.file_comment}\r\n")
        out.write(f"#MapRev={mem.file_maprev}\r\n")
        out.write(f"#EtcData={mem.file_etcdata}\r\n")
        # data

        for line in _dump_memory(mem.mem):
            out.write(line)
            out.write("\r\n")

    _LOG.info("write %s done", file)


def save_raw_memory(file: Path, mem: RadioMemory) -> None:
    """Write RadioMemory to binary file."""
    with file.open("wb") as out:
        out.write(mem.mem)

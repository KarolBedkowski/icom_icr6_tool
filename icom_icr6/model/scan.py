# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
# ruff: noqa: PLR2004
""" """

from __future__ import annotations

import copy
import logging
import typing as ty
from dataclasses import dataclass

from icom_icr6 import consts, validators

from . import _support
from ._support import (
    MutableMemory,
    ValidateError,
    data_set,
    get_index_or_default,
    is_valid_index,
)

_LOG = logging.getLogger(__name__)


@dataclass
class ScanLink:
    idx: int
    name: str
    edges: int

    debug_info: dict[str, object] | None = None

    def links(self) -> ty.Iterable[bool]:
        for idx in range(consts.NUM_SCAN_EDGES):
            yield bool(self.edges & (1 << idx))

    def __getitem__(self, idx: int) -> bool:
        if idx < 0 or idx >= consts.NUM_SCAN_EDGES:
            raise IndexError

        return bool(self.edges & (1 << idx))

    def __setitem__(self, idx: int, value: object) -> None:
        if idx < 0 or idx >= consts.NUM_SCAN_EDGES:
            raise IndexError

        bit = 1 << idx
        self.edges = (self.edges & (~bit)) | (bit if value else 0)

    def clone(self) -> ScanLink:
        return copy.deepcopy(self)

    @classmethod
    def from_data(
        cls: type[ScanLink],
        idx: int,
        data: bytearray | memoryview,
        edata: bytearray | memoryview,
    ) -> ScanLink:
        # 4 bytes, with 7bite padding = 25 bits
        edges = (
            ((edata[3] & 0b1) << 24)
            | (edata[2] << 16)
            | (edata[1] << 8)
            | edata[0]
        )
        return ScanLink(
            idx=idx,
            name=bytes(data[0:6]).decode() if data[0] else "",
            edges=edges,
            debug_info={
                "raw": data.hex(" ", -8),
                "raw_edata": edata.hex(" ", -8),
            }
            if _support.DEBUG
            else None,
        )

    def to_data(self, data: MutableMemory, edata: MutableMemory) -> None:
        data[0:6] = self.name[:6].ljust(6).encode()

        edges = self.edges
        edata[0] = edges & 0xFF
        edata[1] = (edges >> 8) & 0xFF
        edata[2] = (edges >> 16) & 0xFF
        edata[3] = ((edges >> 24) & 1) | 0b11111110

    def remap_edges(self, mapping: dict[int, int]) -> None:
        edges = [
            1 if self.edges & (1 << idx) else 0
            for idx in range(consts.NUM_SCAN_EDGES)
        ]

        dst = edges.copy()
        for idst, isrc in mapping.items():
            dst[idst] = edges[isrc]

        res = 0
        for e in reversed(dst):
            res = (res << 1) | e

        self.edges = res


@dataclass
class ScanEdge:
    idx: int
    start: int
    end: int
    mode: int
    # tuning_step include 15 - "-"
    tuning_step: int
    attenuator: int
    name: str

    # from flags
    hidden: bool

    debug_info: dict[str, object] | None = None
    updated: bool = False

    def clone(self) -> ScanEdge:
        return copy.deepcopy(self)

    def delete(self) -> None:
        self.name = ""
        self.start = self.end = 0
        self.attenuator = consts.ATTENUATOR.index("-")
        self.tuning_step = consts.STEPS.index("-")
        self.mode = consts.MODES_SCAN_EDGES.index("-")
        self.hidden = True

    def unhide(self) -> None:
        self.end = self.end or self.start or 1_000_000
        self.start = self.start or self.end or 1_000_000
        self.hidden = False

    @classmethod
    def from_data(
        cls: type[ScanEdge],
        idx: int,
        data: bytearray | memoryview,
        data_flags: bytearray | memoryview,
    ) -> ScanEdge:
        start = (data[3] << 24) | (data[2] << 16) | (data[1] << 8) | data[0]
        start //= 3
        end = (data[7] << 24) | (data[6] << 16) | (data[5] << 8) | data[4]
        end //= 3

        debug_info = (
            {
                "raw": data.hex(" ", -8),
                "raw_flags": data_flags.hex(" ", -8),
                "start_flags_freq": (data[9] >> 2) & 0b11,
                "end_flags_freq": data[9] & 0b11,
            }
            if _support.DEBUG
            else None
        )

        hidden = bool(data_flags[0] >> 7) or not start or not end

        return ScanEdge(
            idx=idx,
            start=start,
            end=end,
            mode=(data[8] & 0b11110000) >> 4,
            tuning_step=(data[8] & 0b00001111),
            attenuator=(data[9] & 0b00110000) >> 4,
            name=bytes(data[10:16]).decode() if data[10] else "",
            hidden=hidden,
            debug_info=debug_info,
        )

    def to_data(self, data: MutableMemory, data_flags: MutableMemory) -> None:
        start = self.start * 3
        data[0] = start & 0xFF
        data[1] = (start >> 8) & 0xFF
        data[2] = (start >> 16) & 0xFF
        data[3] = (start >> 24) & 0xFF

        end = self.end * 3
        data[4] = end & 0xFF
        data[5] = (end >> 8) & 0xFF
        data[6] = (end >> 16) & 0xFF
        data[7] = (end >> 24) & 0xFF

        data[8] = (self.mode & 0b1111) << 4 | (self.tuning_step & 0b1111)

        data_set(data, 9, 0b00110000, self.attenuator << 4)

        if self.name:
            data[10:16] = self.name[:6].ljust(6).encode()
        else:
            data[10:16] = bytes([0, 0, 0, 0, 0, 0])

        if self.hidden:
            data_flags[0] = data_flags[2] = 0xFF
        else:
            data_flags[0] = data_flags[2] = 0x7F

    def validate(self) -> None:
        if self.idx < 0 or self.idx >= consts.NUM_SCAN_EDGES:
            raise ValidateError("idx", self.idx)

        if not validators.validate_frequency(self.start):
            raise ValidateError("idx", self.start)

        if not validators.validate_frequency(self.end):
            raise ValidateError("freq", self.end)

        is_valid_index(consts.MODES_SCAN_EDGES, self.mode, "mode")
        if self.mode == 3:
            # "auto" is not used
            raise ValidateError("mode", self.mode)

        is_valid_index(consts.STEPS, self.tuning_step, "tuning step")
        if self.tuning_step == 14:
            # "auto" is not valid
            raise ValidateError("tuning_step", self.tuning_step)

        is_valid_index(consts.ATTENUATOR, self.attenuator, "attenuator")

        try:
            validators.validate_name(self.name)
        except ValueError as err:
            raise ValidateError("name", self.name) from err

    def to_record(self) -> dict[str, object]:
        return {
            "idx": self.idx,
            "start": self.start,
            "end": self.end,
            "mode": consts.MODES_SCAN_EDGES[self.mode],
            "ts": consts.STEPS[self.tuning_step],
            "att": consts.ATTENUATOR[self.attenuator],
            "name": self.name.rstrip(),
        }

    def from_record(self, data: dict[str, object]) -> None:
        _LOG.debug("from_record: %r", data)
        if (idx := data.get("idx")) is not None:
            self.idx = int(idx)  # type: ignore

        if (start := data.get("start")) is not None:
            self.start = int(start or "0")  # type: ignore

        if (end := data.get("end")) is not None:
            self.end = int(end or "0")  # type: ignore

        if mode := data.get("mode"):
            self.mode = consts.MODES.index(str(mode))
            if self.mode == 3:
                # map "auto" to "-"
                self.mode = 4

        if ts := data.get("ts"):
            self.tuning_step = consts.STEPS.index(str(ts))
            if self.tuning_step == 14:
                # map "auto" tuning_step to "-"
                self.tuning_step = 15

        if att := data.get("att"):
            self.attenuator = get_index_or_default(
                consts.ATTENUATOR, str(att), 2
            )

        if name := data.get("name"):
            self.name = str(name)

# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
# ruff: noqa: PLR2004
""" """

from __future__ import annotations

import binascii
from dataclasses import dataclass

from . import _support


@dataclass
class RadioModel:
    # Data format - 39B
    # model: 4B
    # unknown: 1B
    # rev: 1B
    # comment: 16B
    # region: 1B
    # unknown: 1B = 0?
    # region flags: 1B (usable lower 1 or 2 bits?)
    # serial 14B (hex)
    #    4B
    #    1B unknown
    #    2B
    model: bytes
    rev: int
    comment: str
    serial: str

    region: int
    etc_data_flags: int

    debug_info: dict[str, object] | None = None

    @classmethod
    def from_data(
        cls: type[RadioModel], data: bytes | bytearray | memoryview
    ) -> RadioModel:
        serial = binascii.unhexlify(data[25 : 25 + 14])
        serial_decoded = (
            f"{serial[0] << 8 | serial[1]:04d}"
            f"{serial[2]:02d}{serial[3]:02d}"
            f"{serial[5] << 8 | serial[6]:04d}"
        )

        debug_info = (
            {
                "raw": data.hex(" ", -8),
                "unk1": data[4],
                "unk2": data[23],
                "unk_serial": serial[4],
            }
            if _support.DEBUG
            else None
        )

        return RadioModel(
            model=bytes(data[0:4]),
            rev=data[5],
            comment=bytes(data[6:22]).decode(),
            serial=serial_decoded,
            region=data[22],
            etc_data_flags=data[24],
            debug_info=debug_info,
        )

    def is_icr6(self) -> bool:
        return self.model == b"\x32\x50\x00\x01"

    def human_model(self) -> str:
        return self.model.hex()

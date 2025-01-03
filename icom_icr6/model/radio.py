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
    # Data format - 40B
    # model: 4B
    # unknown: 1B - is this mapped to region?
    # rev: 1B
    # comment: 16B
    # unknown: 3B
    # serial 14B
    #    4B
    #    1B unknown
    #    2B
    # unknown 7B
    model: bytes
    rev: int
    comment: str
    serial: str

    debug_info: dict[str, object] | None = None

    @classmethod
    def from_data(
        cls: type[RadioModel], data: bytes | bytearray | memoryview
    ) -> RadioModel:
        serial = binascii.unhexlify(data[25 : 25 + 14])
        serial_decoded = (
            f"{serial[0]<<8|serial[1]:04d}"
            f"{serial[2]:02d}{serial[3]:02d}"
            f"{serial[5]<<8|serial[6]:04d}"
        )

        debug_info = (
            {
                "raw": data.hex(" ", -8),
                "unk1": data[4],
                "unk2": data[22:25],
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
            debug_info=debug_info,
        )

    def is_icr6(self) -> bool:
        return self.model == b"\x32\x50\x00\x01"

    def human_model(self) -> str:
        return self.model.hex()

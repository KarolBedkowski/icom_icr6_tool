# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
# ruff: noqa: PLR2004
"""
Support function for model objects.
"""

from __future__ import annotations

import typing as ty
from collections import abc

DEBUG = False

MutableMemory = abc.MutableSequence[int] | memoryview


def is_valid_index(inlist: ty.Collection[object], idx: int, name: str) -> None:
    if idx < 0 or idx >= len(inlist):
        raise ValidateError(name, idx)


def try_get(inlist: ty.Sequence[str], idx: int) -> str:
    try:
        return inlist[idx]
    except IndexError:
        return f"<[{idx}]>"


def get_index_or_default(
    inlist: ty.Sequence[str], value: object, default: int = 0
) -> int:
    strval = value if isinstance(value, str) else str(value)
    try:
        return inlist.index(strval)
    except ValueError:
        return default


def obj2bool(val: object) -> bool:
    if isinstance(val, str):
        return val.lower() in ("yes", "y", "true", "t")

    return bool(val)


def bool2bit(val: object, mask: int) -> int:
    return mask if val else 0


def data_set_bit(
    data: MutableMemory,
    offset: int,
    bit: int,
    value: object,
) -> None:
    """Set one `bit` in byte `data[offset]` to `value`."""
    if value:
        data[offset] = data[offset] | (1 << bit)
    else:
        data[offset] = data[offset] & (~(1 << bit))


def data_set(
    data: MutableMemory,
    offset: int,
    mask: int,
    value: int,
) -> None:
    """Set bits indicated by `mask` in byte `data[offset]` to `value`."""
    data[offset] = (data[offset] & (~mask)) | (value & mask)


class ValidateError(ValueError):
    def __init__(self, field_name: str, value: object) -> None:
        self.field = field_name
        self.value = value

    def __str__(self) -> str:
        return f"invalid value in {self.field}: {self.value!r}"

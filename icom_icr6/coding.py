# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

from __future__ import annotations

import logging
import typing as ty

from . import consts

if ty.TYPE_CHECKING:
    from collections import abc

_LOG = logging.getLogger(__name__)


def decode_name(inp: abc.Sequence[int]) -> str:
    """Decode name from 5-bytes that contains 6 - 6bits coded characters with
    4-bit padding on beginning..

          76543210
       0  xxxx0000
       1  00111111
       2  22222233
       3  33334444
       4  44555555
    """
    if len(inp) != consts.ENCODED_NAME_LEN:
        raise ValueError

    chars = (
        (inp[0] & 0b00001111) << 2 | (inp[1] & 0b11000000) >> 6,
        (inp[1] & 0b00111111),
        (inp[2] & 0b11111100) >> 2,
        (inp[2] & 0b00000011) << 4 | (inp[3] & 0b11110000) >> 4,
        (inp[3] & 0b00001111) << 2 | (inp[4] & 0b11000000) >> 6,
        (inp[4] & 0b00111111),
    )

    name = "".join(consts.CODED_CHRS[x] for x in chars)
    if name and name[0] == "^":
        # invalid name
        return ""

    return name.rstrip()


def encode_name(inp: str) -> abc.Sequence[int]:
    inp = inp[: consts.NAME_LEN].upper().ljust(consts.NAME_LEN)

    iic = [0 if x == "^" else consts.CODED_CHRS.index(x) for x in inp]
    return [
        (iic[0] & 0b00111100) >> 2,  # padding
        ((iic[0] & 0b00000011) << 6) | (iic[1] & 0b00111111),
        ((iic[2] & 0b00111111) << 2) | ((iic[3] & 0b00110000) >> 4),
        ((iic[3] & 0b00001111) << 4) | ((iic[4] & 0b00111100) >> 2),
        ((iic[4] & 0b00000011) << 6) | (iic[5] & 0b00111111),
    ]


def decode_freq(freq: int, flags: int) -> int:
    """
    flags are probably only 2 bits:
        00 -> 5000
        01 -> 6250
        10 -> 8333.3333
        11 -> 9000
    """
    # TODO: check:
    match flags:
        case 0b00:
            return 5000 * freq
        case 0b01:
            return 6250 * freq
        case 0b10:
            return (25000 * freq) // 3  # unused?
        case 0b11:
            return 9000 * freq

    _LOG.error("unknown flag %r for freq %r", flags, freq)
    raise ValueError


class EncodedFreq(ty.NamedTuple):
    flags: int
    freq: int
    offset: int

    def freq_bytes(self) -> tuple[int, int, int]:
        # freq0, freq1, freq2
        return (
            self.freq & 0x00FF,
            (self.freq & 0xFF00) >> 8,
            (self.freq & 0x30000) >> 16,
        )

    def offset_bytes(self) -> tuple[int, int]:
        # offset_l, offset_h
        return self.offset & 0x00FF, (self.offset & 0xFF00) >> 8


class InvalidFlagError(ValueError):
    pass


def encode_freq(freq: int, offset: int) -> EncodedFreq:
    # freq min 0.1MHz
    # offset max 159.995 MHz
    # flag is <offset_flag:2b><freq_flag:2b>
    flags = 0
    # 9k step only for freq <= 1620k
    if freq % 9000 == freq % 5000 == 0 and freq <= consts.MAX_FREQ_FOR_9K_MUL:
        flags = 0b0 if offset else 0b1111  # 9k step only for freq <= 1620k
    elif freq % 9000 == 0 and freq <= consts.MAX_FREQ_FOR_9K_MUL:
        flags = 0b011 if offset else 0b1111  # 9k step only for freq <= 1620k
    elif freq % 5000 == 0:
        flags = 0
    elif freq % 6250 == 0:
        flags = 0b01 if offset else 0b0101
    elif (freq * 3) % 25000 == 0:  # not used?
        flags = 0b1010
    else:
        raise InvalidFlagError

    match flags & 0b11:
        case 0b11:  # 9k
            return EncodedFreq(flags, freq // 9000, offset // 9000)
        case 0b10:  # 8333.333
            return EncodedFreq(
                flags, (freq * 3) // 25000, (offset * 3) // 25000
            )
        case 0b01:  # 6250
            return EncodedFreq(flags, freq // 6250, offset // 6250)
        case 0b00:  # 5k
            return EncodedFreq(flags, freq // 5000, offset // 5000)

    raise ValueError

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
    """Decode frequency - multiple `freq` by `flags`.

    flags are only 2 bits:
        00 -> 5000
        01 -> 6250
        10 -> 8333.3333
        11 -> 9000
    """

    match flags:
        case 0b00:
            return 5000 * freq
        case 0b01:
            return 6250 * freq
        case 0b10:
            return (25000 * freq) // 3
        case 0b11:
            return 9000 * freq

    _LOG.error("unknown flag %r for freq %r", flags, freq)
    raise ValueError


class EncodedFreq(ty.NamedTuple):
    flags: int
    freq: int
    offset: int

    def __repr__(self) -> str:
        return (
            f"EncodedFreq(flags={self.flags:04b}, freq={self.freq}, "
            f"offset={self.offset})"
        )

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


def _find_div_for_freq(freq: int, avail: tuple[int, ...]) -> ty.Iterable[int]:
    if not freq:
        return

    if 0 in avail and freq % 5000 == 0:
        yield 0

    if 1 in avail and freq % 6250 == 0:
        yield 1

    # if 2 in avail and int(freq * 3 / 25000 + 0.5) * 25000 // 3 == freq:
    #     yield 2
    if 2 in avail and (not freq % 8333 or freq % 10 in (3, 6)):  # noqa: PLR2004
        yield 2

    if 3 in avail and freq % 9000 == 0:  # noqa: PLR2004
        yield 3


def _div_freq(freq: int, freq_div: int) -> int:
    match freq_div:
        case 0b00:  # 5k
            nfreq = freq // 5000
        case 0b01:  # 6250
            nfreq = freq // 6250
        case 0b10:  # 8333.333
            nfreq = round((freq * 3) / 25000.0)
        case 0b11:  # 9k
            nfreq = freq // 9000

    return nfreq


def encode_freq(freq: int, offset: int) -> EncodedFreq:
    # freq min 0.1MHz
    # offset max 159.995 MHz
    # flag is <offset_flag:2b><freq_flag:2b
    # preferred order: 9k, 5k, 6250, 8333
    # TODO: probably this is not dependent on frequency

    if freq == 0:
        return EncodedFreq(0, 0, 0)

    fset: tuple[int, ...] = (3, 0, 1)  # 9k, 5k, 6250
    if consts.is_air_band(freq):
        fset = (0, 1, 2)  # 5k, 6250, 8333.33

    fd = set(_find_div_for_freq(freq, fset))
    od = set(_find_div_for_freq(offset, fset)) if offset else set()

    if offset:
        if common := fd & od:
            # there is common divider for freq & offset
            freq_div = offset_div = 3 if 3 in common else min(common)  # noqa: PLR2004
        else:
            # prefer 9k in offset when available
            freq_div = 3 if 3 in fd else min(fd)  # noqa: PLR2004
            offset_div = 3 if 3 in od else min(od)  # noqa: PLR2004
    else:
        # when 9k is available for freq, set it for for freq and offset
        offset_div = freq_div = 3 if 3 in fd else min(fd)  # noqa: PLR2004

    return EncodedFreq(
        (offset_div << 2) | freq_div,
        _div_freq(freq, freq_div),
        _div_freq(offset, offset_div),
    )


def etcdata_to_region(etcdata: str) -> tuple[int, int]:
    """Etcdata contain 5 bits of "region" + unknown flags (two bit).
    Rest is checksum - arithmetic sum of all "1" in region and
    flags & 7. Bits: (r=region, C=checksum, f=some flag)
        fedcba98 76543210
        000000rr rCrrCffC

    Return: (region, flags)
    Raise: ValueError on invalid checksum

    """
    etc = int(etcdata, 16)
    region = ((etc & 0b1110000000) >> 5) | ((etc & 0b110000) >> 4)
    flags = (etc & 0b110) >> 1

    # check checksum
    cs = ((etc >> 4) & 0b100) | ((etc >> 2) & 0b10) | (etc & 1)
    ccs = (flags.bit_count() + region.bit_count()) & 0b111
    if cs != ccs:
        raise ValueError

    return region, flags


def region_to_etcdata(region: int, flags: int) -> str:
    """Encode region and flags into etcdata."""
    # there are 2 flags
    flags = flags & 0b11

    # checksum is number of 1 in region and flags - only 3 bits
    cs = flags.bit_count() + region.bit_count()

    etcdata = (
        ((region & 0b11100) << 5)
        | ((cs & 0b100) << 4)
        | ((region & 0b11) << 4)
        | ((cs & 0b010) << 2)
        | (flags << 1)
        | (cs & 1)
    )
    return f"{etcdata:04X}"


def civ_decode_freq(inp: bytes) -> int:
    return (
        (inp[4] >> 4) * 1_000_000_000
        + (inp[4] & 0x0F) * 100_000_000
        + (inp[3] >> 4) * 10_000_000
        + (inp[3] & 0x0F) * 1_000_000
        + (inp[2] >> 4) * 100_000
        + (inp[2] & 0x0F) * 10_000
        + (inp[1] >> 4) * 1_000
        + (inp[1] & 0x0F) * 100
        + (inp[0] >> 4) * 10
        + (inp[0] & 0x0F)
    )


def civ_encode_freq(freq: int) -> bytes:
    res = []
    t = freq
    for _ in range(5):
        t, v1 = divmod(t, 10)
        t, v2 = divmod(t, 10)
        res.append((v2 << 4) | v1)

    return bytes(res)


def civ_decode_dec_bytes(data: bytes) -> int:
    """decode 2 bytes in bcd encoding into int."""
    return (
        (data[0] >> 4) * 1000
        + (data[0] & 0xF) * 100
        + (data[1] >> 4) * 10
        + (data[1] & 0xF)
    )


def civ_encode_dec_bytes(inp: int) -> bytes:
    """decode 2 bytes in bcd encoding into int."""
    t, v1 = divmod(inp, 10)
    t, v2 = divmod(t, 10)
    t, v3 = divmod(t, 10)
    t, v4 = divmod(t, 10)
    return bytes([(v4 << 4) | v3, (v2 << 4) | v1])

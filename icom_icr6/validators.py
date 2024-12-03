# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

from . import coding, consts


def validate_frequency(inp: str | int) -> bool:
    if isinstance(inp, str):
        try:
            freq = int(inp)
        except ValueError:
            return False
    else:
        freq = inp

    if freq > consts.MAX_FREQUENCY or freq < 0:
        return False

    try:
        coding.encode_freq(freq, 0)
    except ValueError:
        return False

    return True


def validate_offset(freq: int, inp: str | int) -> bool:
    if isinstance(inp, str):
        try:
            offset = int(inp)
        except ValueError:
            return False
    else:
        offset = inp

    if offset == 0:
        return True

    if offset > consts.MAX_OFFSET or offset < consts.MIN_OFFSET:
        return False

    try:
        coding.encode_freq(freq, offset)
    except ValueError:
        return False

    return True


def validate_name(name: str) -> None:
    if len(name) > consts.MAX_NAME_LEN:
        raise ValueError

    if any(i not in consts.VALID_CHAR for i in name.upper()):
        raise ValueError


def validate_comment(comment: str) -> None:
    if len(comment) > consts.MAX_COMMENT_LEN:
        raise ValueError

    if any(i not in consts.VALID_CHAR for i in comment.upper()):
        raise ValueError

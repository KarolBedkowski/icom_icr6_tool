# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
# pylint: disable=protected-access,unspecified-encoding,consider-using-with
# mypy: allow-untyped-defs, allow-untyped-calls
# ruff: noqa: SLF001,PLR2004

""" """

from icom_icr6 import model


def test_decode_radio_model():
    inp = (
        "32500001"
        "23"
        "01"
        "20202020202020202020202020202020"
        "010001"
        "3043423233453330303030314137"
    )
    with memoryview(bytearray.fromhex(inp)) as data:
        rm = model.RadioModel.from_data(data)

    assert rm.model == b"2P\x00\x01"
    assert rm.rev == 1
    assert rm.serial == "325062480423"
    assert rm.comment == "                "


def test_decode_radio_model2():
    inp = (
        "32500001"
        "23"
        "01"
        "434F4D4D454E54313233343536373839"
        "010001"
        "3043423233453330313230324137"
    )
    data = bytearray.fromhex(inp)
    rm = model.RadioModel.from_data(data)

    assert rm.model == b"2P\x00\x01"
    assert rm.rev == 1
    assert rm.serial == "325062480679"
    assert rm.comment == "COMMENT123456789"

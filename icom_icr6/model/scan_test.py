# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
# pylint: disable=protected-access,unspecified-encoding,consider-using-with
# mypy: allow-untyped-defs, allow-untyped-calls
# ruff: noqa: SLF001,PLR2004

""" """

import binascii

from icom_icr6 import model


def test_scan_edge1():
    inp = b"e0930400004775e84f20414c4c202020"
    inp_flags = b"7fff7f"
    data = bytearray(binascii.unhexlify(inp))
    data_flags = bytearray(binascii.unhexlify(inp_flags))
    se = model.ScanEdge.from_data(0, data, data_flags)

    assert se.idx == 0
    assert se.start == 100000
    assert se.end == 1300000000
    assert se.mode == 4
    assert se.tuning_step == 15
    assert se.attenuator == 2
    assert se.name == "ALL   "
    assert not se.hidden

    o_data = data[:]
    o_data_flags = data_flags[:]
    se.to_data(o_data, o_data_flags)
    assert o_data == data
    assert o_data_flags == data_flags


def test_scan_edge2():
    inp = b"f08e3500804a5d05202353572d574156"
    inp_flags = b"7fff7f"
    data = bytearray(binascii.unhexlify(inp))
    data_flags = bytearray(binascii.unhexlify(inp_flags))
    se = model.ScanEdge.from_data(20, data, data_flags)

    assert se.idx == 20
    assert se.start == 1170000
    assert se.end == 30000000
    assert se.mode == 2
    assert se.tuning_step == 0
    assert se.attenuator == 2
    assert se.name == "SW-WAV"
    assert not se.hidden

    o_data = data[:]
    o_data_flags = data_flags[:]
    se.to_data(o_data, o_data_flags)
    assert o_data == data
    assert o_data_flags == data_flags


def test_scan_edge3():
    inp = b"0000000000000000000f202020202020"
    inp_flags = b"ffffff"
    data = bytearray(binascii.unhexlify(inp))
    data_flags = bytearray(binascii.unhexlify(inp_flags))
    se = model.ScanEdge.from_data(24, data, data_flags)
    assert se.idx == 24
    assert se.start == 0
    assert se.end == 0
    assert se.mode == 0
    assert se.tuning_step == 0
    assert se.attenuator == 0
    assert se.name == "      "
    assert se.hidden

    o_data = data[:]
    o_data_flags = data_flags[:]
    se.to_data(o_data, o_data_flags)
    assert o_data == data
    assert o_data_flags == data_flags


def test_scan_link1():
    inp = b"434220202020ffff"
    inp_e = b"000c00fe"
    data = bytearray(binascii.unhexlify(inp))
    data_e = bytearray(binascii.unhexlify(inp_e))
    sl = model.ScanLink.from_data(1, data, data_e)
    assert sl.idx == 1
    assert sl.name == "CB    "
    assert sl.edges == 3072

    links = list(sl.links())
    exp_links = [
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
    ]
    assert links == exp_links

    for idx, el in enumerate(exp_links):
        assert sl[idx] == el

    o_data = data[:]
    o_data_e = data_e[:]

    sl.to_data(o_data, o_data_e)
    assert o_data == data
    assert o_data_e == data_e

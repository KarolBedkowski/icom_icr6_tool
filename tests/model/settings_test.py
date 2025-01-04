# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
# pylint: disable=protected-access,unspecified-encoding,consider-using-with
# mypy: allow-untyped-defs, allow-untyped-calls
# ruff: noqa: SLF001,PLR2004

""" """

from icom_icr6 import model


def test_decode_settings():
    inp = (
        "2020202020202020202020200001000109000101000100010004090600020000"
        "00007e050100ffffffffffffffffff0600ff00002acd00000000ff001301ffff"
    )
    data = bytearray.fromhex(inp)
    sett = model.RadioSettings.from_data(data)

    assert not sett.af_filer_am
    assert not sett.af_filer_fm
    assert not sett.af_filer_wfm
    assert sett.am_ant == 1
    assert sett.auto_power_off == 4
    assert sett.backlight == 0
    assert sett.beep_level == 9
    assert sett.charging_type == 0
    assert sett.civ_address == 126
    assert sett.civ_baud_rate == 5
    assert sett.civ_transceive
    assert sett.dial_function == 0
    assert sett.dial_speed_up
    assert sett.fm_ant == 0
    assert sett.func_dial_step == 1
    assert sett.key_beep
    assert sett.key_lock == 0
    assert sett.lcd_contrast == 2
    assert sett.mem_display_type == 2
    assert sett.monitor == 0
    assert sett.pause_timer == 9
    assert sett.power_save
    assert sett.program_skip_scan
    assert sett.resume_timer == 6
    assert sett.set_expand
    assert not sett.stop_beep
    assert not sett.wx_alert
    assert sett.wx_channel == 0

    o_data = data[:]
    sett.to_data(o_data)
    assert o_data == data


def test_decode_settings2():
    inp = (
        "2020202020202020202020200001000100020100000000010000040200010000"
        "00007e050101ffffffffffffffffff0600ff000028cd00000000ff001301ffff"
    )
    data = bytearray.fromhex(inp)
    sett = model.RadioSettings.from_data(data)
    assert not sett.af_filer_am
    assert not sett.af_filer_fm
    assert not sett.af_filer_wfm
    assert sett.am_ant == 0
    assert sett.auto_power_off == 0
    assert sett.backlight == 2
    assert sett.beep_level == 0
    assert sett.charging_type == 1
    assert sett.civ_address == 126
    assert sett.civ_baud_rate == 5
    assert sett.civ_transceive
    assert sett.dial_function == 0
    assert sett.dial_speed_up
    assert sett.fm_ant == 0
    assert sett.func_dial_step == 1
    assert sett.key_beep
    assert sett.key_lock == 0
    assert sett.lcd_contrast == 1
    assert sett.mem_display_type == 0
    assert sett.monitor == 0
    assert sett.pause_timer == 4
    assert sett.power_save
    assert sett.program_skip_scan
    assert sett.resume_timer == 2
    assert not sett.set_expand
    assert not sett.stop_beep
    assert not sett.wx_alert
    assert sett.wx_channel == 0

    o_data = data[:]
    sett.to_data(o_data)
    assert o_data == data


def test_decode_settings3():
    inp = (
        "2020202020202020202020200002000023020000010002000102030201000001"
        "01017f030001ffffffffffffffffff0600ff000039c500000000ff001301ffff"
    )
    data = bytearray.fromhex(inp)
    sett = model.RadioSettings.from_data(data)
    assert sett.af_filer_am
    assert sett.af_filer_fm
    assert sett.af_filer_wfm
    assert sett.am_ant == 0
    assert sett.auto_power_off == 2
    assert sett.backlight == 2
    assert sett.beep_level == 35
    assert sett.charging_type == 1
    assert sett.civ_address == 127
    assert sett.civ_baud_rate == 3
    assert not sett.civ_transceive
    assert sett.dial_function == 1
    assert not sett.dial_speed_up
    assert sett.fm_ant == 1
    assert sett.func_dial_step == 2
    assert not sett.key_beep
    assert sett.key_lock == 2
    assert sett.lcd_contrast == 0
    assert sett.mem_display_type == 1
    assert sett.monitor == 1
    assert sett.pause_timer == 3
    assert not sett.power_save
    assert not sett.program_skip_scan
    assert sett.resume_timer == 2
    assert not sett.set_expand
    assert sett.stop_beep
    assert not sett.wx_alert
    assert sett.wx_channel == 0

    o_data = data[:]
    sett.to_data(o_data)
    assert o_data == data


def test_bands1():
    inp = "d0dd060000000000000800002000e808"
    data = bytearray.fromhex(inp)
    band = model.BandDefaults.from_data(0, data)

    assert band.freq == 150000
    assert band.offset == 0
    assert band.tuning_step == 0
    assert band.tsql_freq == 8
    assert band.dtcs == 0
    assert band.mode == 2
    assert band.canceller_freq == 59400
    assert band.duplex == 0
    assert band.tone_mode == 0
    assert not band.vsc
    assert band.canceller == 0
    assert band.polarity == 0
    assert not band.af_filter
    assert not band.attenuator


def test_bands2():
    inp = "80d6e34c80e65b01080800000000e808"
    data = bytearray.fromhex(inp)
    band = model.BandDefaults.from_data(0, data)

    assert band.freq == 430000000
    assert band.offset == 7600000
    assert band.tuning_step == 8
    assert band.tsql_freq == 8
    assert band.dtcs == 0
    assert band.mode == 0
    assert band.canceller_freq == 59400
    assert band.duplex == 0
    assert band.tone_mode == 0
    assert not band.vsc
    assert band.canceller == 0
    assert band.polarity == 0
    assert not band.af_filter
    assert not band.attenuator

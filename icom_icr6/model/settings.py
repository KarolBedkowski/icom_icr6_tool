# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
# ruff: noqa: PLR2004
""" """

from __future__ import annotations

import binascii
import copy
from dataclasses import dataclass

from ._support import DEBUG, MutableMemory, data_set, data_set_bit


@dataclass
class RadioSettings:
    af_filer_am: bool
    af_filer_fm: bool
    af_filer_wfm: bool
    am_ant: int
    auto_power_off: int  # 0 - 6
    backlight: int
    beep_level: int
    charging_type: int  # 0-1
    civ_address: int
    civ_baud_rate: int
    civ_transceive: bool
    dial_function: int  # 0-1
    dial_speed_up: bool
    fm_ant: int
    func_dial_step: int
    key_beep: bool
    key_lock: int  # 0-3
    lcd_contrast: int  # 0-4 -> 1-5
    mem_display_type: int
    monitor: int  # 0=push, 1=hold
    pause_timer: int  # 0-10
    power_save: bool
    program_skip_scan: bool
    resume_timer: int  # 0 -6
    set_expand: bool
    stop_beep: bool
    wx_alert: bool
    wx_channel: int  # 0-9 -> 1-10

    debug_info: dict[str, object] | None = None
    updated: bool = False

    def clone(self) -> RadioSettings:
        return copy.deepcopy(self)

    @classmethod
    def from_data(
        cls: type[RadioSettings], data: bytearray | memoryview
    ) -> RadioSettings:
        debug_info = (
            {
                "raw": binascii.hexlify(data),
                "priority_scan_type": data[14] & 0b111,
                "scanning_band": data[47],
                "scanning_bank": data[50],
                "scan_enabled": bool(data[52] & 0b01000000),
                "mem_scan_priority": bool(data[52] & 0b00001000),
                "scan_mode": (data[52] & 0b00000100) >> 2,
                "refresh_flag": bool(data[53] & 0b10000000),
                "unprotected_frequency_flag": bool(data[53] & 0b01000000),
                "autowrite_memory": bool(data[53] & 0b00100000),
                "keylock": bool(data[53] & 0b00010000),
                "priority_scan": bool(data[53] & 0b00000010),
                "scan_direction": bool(data[53] & 0b00000001),
                "scan_vfo_type": data[54],
                "scan_mem_type": data[55],
                "mem_chan_data": data[56],
            }
            if DEBUG
            else None
        )

        return RadioSettings(
            func_dial_step=data[13] & 0b00000011,
            key_beep=bool(data[15] & 1),
            beep_level=data[16] & 0b00111111,
            backlight=data[17] & 0b00000011,
            power_save=bool(data[18] & 1),
            am_ant=data[19] & 1,
            fm_ant=data[20] & 1,
            set_expand=bool(data[21] & 1),
            key_lock=data[22] & 0b00000011,
            dial_speed_up=bool(data[23] & 1),
            monitor=data[24] & 1,
            auto_power_off=data[25] & 0b00000111,
            pause_timer=data[26] & 0b00001111,
            resume_timer=data[27] & 0b00000111,
            stop_beep=bool(data[28] & 1),
            lcd_contrast=data[29] & 0b00000111,
            af_filer_fm=bool(data[31] & 1),
            af_filer_wfm=bool(data[32] & 1),
            af_filer_am=bool(data[33] & 1),
            civ_address=data[34],
            civ_baud_rate=data[35] & 0b00000111,
            civ_transceive=bool(data[36] & 1),
            charging_type=data[37] & 1,
            dial_function=(data[52] & 0b00010000) >> 4,
            mem_display_type=data[52] & 0b00000011,
            program_skip_scan=bool(data[53] & 0b00001000),
            wx_alert=bool(data[30]),
            wx_channel=data[59],
            debug_info=debug_info,
        )

    def to_data(self, data: MutableMemory) -> None:
        data_set(data, 13, 0b11, self.func_dial_step)
        data_set_bit(data, 15, 0, self.key_beep)
        data_set(data, 16, 0b00111111, self.beep_level)
        data_set(data, 17, 0b11, self.backlight)
        data_set_bit(data, 18, 0, self.power_save)
        data_set_bit(data, 19, 0, self.am_ant)
        data_set_bit(data, 20, 0, self.fm_ant)
        data_set_bit(data, 21, 0, self.set_expand)
        data_set(data, 22, 0b11, self.key_lock)
        data_set_bit(data, 23, 0, self.dial_speed_up)
        data_set_bit(data, 24, 0, self.monitor)
        data_set(data, 25, 0b111, self.auto_power_off)
        data_set(data, 26, 0b1111, self.pause_timer)
        data_set(data, 27, 0b111, self.resume_timer)
        data_set_bit(data, 28, 0, self.stop_beep)
        data_set(data, 29, 0b111, self.lcd_contrast)
        data[30] = 1 if self.wx_alert else 0
        data_set_bit(data, 31, 0, self.af_filer_fm)
        data_set_bit(data, 32, 0, self.af_filer_wfm)
        data_set_bit(data, 33, 0, self.af_filer_am)
        data[34] = self.civ_address
        data_set(data, 35, 0b00000111, self.civ_baud_rate)
        data_set_bit(data, 36, 0, self.civ_transceive)
        data_set_bit(data, 37, 0, self.charging_type)
        data_set_bit(data, 52, 4, self.dial_function)
        data_set(data, 52, 0b11, self.mem_display_type)
        data_set_bit(data, 53, 3, self.program_skip_scan)
        data[59] = max(min(self.wx_channel, 9), 0)


@dataclass
class BandDefaults:
    idx: int
    freq: int
    offset: int
    tuning_step: int
    tsql_freq: int
    dtcs: int
    mode: int
    canceller_freq: int
    duplex: int
    tone_mode: int
    vsc: bool
    canceller: int
    polarity: int
    af_filter: bool
    attenuator: bool

    debug_info: dict[str, object] | None

    @classmethod
    def from_data(
        cls: type[BandDefaults],
        idx: int,
        data: bytearray | memoryview,
    ) -> BandDefaults:
        freq = (data[3] << 24) | (data[2] << 16) | (data[1] << 8) | data[0]
        freq //= 3
        offset = (data[7] << 24) | (data[6] << 16) | (data[5] << 8) | data[4]
        offset //= 3

        debug_info = (
            {
                "raw": binascii.hexlify(data),
                "unknown6": data[11],
            }
            if DEBUG
            else None
        )

        return BandDefaults(
            idx=idx,
            freq=freq,
            offset=offset,
            tuning_step=data[8] & 0b1111,
            tsql_freq=data[9] & 0b111111,
            dtcs=data[10] & 0b01111111,
            mode=(data[12] & 0b00110000) >> 4,
            canceller_freq=(data[14] << 8) | data[15],
            duplex=(data[12] >> 6),
            tone_mode=data[12] & 0b1111,
            vsc=bool(data[13] & 0b01000000),
            canceller=(data[13] & 0b00110000) >> 4,
            polarity=(data[13] & 0b00000100) >> 2,
            af_filter=bool(data[13] & 0b00000010),
            attenuator=bool(data[13] & 0b0000001),
            debug_info=debug_info,
        )

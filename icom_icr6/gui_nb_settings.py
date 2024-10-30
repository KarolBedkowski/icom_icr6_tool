# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from contextlib import suppress
from tkinter import messagebox, ttk

from . import gui_model, model
from .gui_widgets import new_checkbox, new_combo, new_entry

_LOG = logging.getLogger(__name__)


class SettingsPage(tk.Frame):
    def __init__(
        self, parent: tk.Widget, radio_memory: model.RadioMemory
    ) -> None:
        super().__init__(parent)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)
        self.columnconfigure(3, weight=1)
        self.columnconfigure(4, weight=0)
        self.columnconfigure(5, weight=1)

        self._radio_memory = radio_memory
        self._create_vars()
        self._create_fields()

    def set(self, radio_memory: model.RadioMemory) -> None:
        self._radio_memory = radio_memory
        self.__fill()

    def _create_vars(self) -> None:
        self._var_func_dial_step = tk.StringVar()
        self._var_key_beep = tk.IntVar()
        self._var_beep_level = tk.StringVar()
        self._var_backlight = tk.StringVar()
        self._var_power_save = tk.IntVar()
        self._var_am_ant = tk.StringVar()
        self._var_fm_ant = tk.StringVar()
        self._var_civ_address = tk.StringVar()
        self._var_civ_baud_rate = tk.StringVar()
        self._var_civ_transceive = tk.IntVar()
        self._var_dial_function = tk.StringVar()
        self._var_mem_display_type = tk.StringVar()
        self._var_program_skip_scan = tk.IntVar()
        self._var_bank_links = [tk.IntVar() for _ in range(22)]
        self._var_pause_timer = tk.StringVar()
        self._var_resume_timer = tk.StringVar()
        self._var_stop_beep = tk.IntVar()
        self._var_set_expand = tk.IntVar()
        self._var_key_lock = tk.StringVar()
        self._var_dial_speed_up = tk.IntVar()
        self._var_monitor = tk.StringVar()
        self._var_auto_power_off = tk.IntVar()
        self._var_lcd_contrast = tk.StringVar()
        self._var_af_filer_fm = tk.IntVar()
        self._var_af_filer_wfm = tk.IntVar()
        self._var_af_filer_am = tk.IntVar()
        self._var_charging_type = tk.StringVar()

    def _create_fields(self) -> None:
        new_combo(
            self,
            0,
            0,
            "Func-Down/Up",
            self._var_charging_type,
            model.SETT_FUNC_DIAL_STEP,
        )
        new_combo(
            self,
            0,
            2,
            "Dial function",
            self._var_dial_function,
            model.SETT_DIAL_FUNCTION,
        )
        new_checkbox(self, 0, 4, "Dial speed up", self._var_dial_speed_up)

        new_checkbox(self, 1, 0, "Auto power save", self._var_power_save)
        new_checkbox(self, 1, 2, "Auto power off", self._var_auto_power_off)

        new_checkbox(self, 2, 0, "Key beep", self._var_key_beep)
        new_combo(
            self,
            2,
            2,
            "Beep level",
            self._var_beep_level,
            model.SETT_BEEP_LEVEL,
        )

        new_combo(
            self, 3, 0, "Key lock", self._var_key_lock, model.SETT_KEY_LOCK
        )
        new_combo(self, 3, 2, "Monitor", self._var_monitor, model.SETT_MONITOR)

        new_combo(
            self, 4, 0, "Backlight", self._var_backlight, model.SETT_BACKLIGHT
        )
        new_combo(
            self,
            4,
            2,
            "Memory display type",
            self._var_mem_display_type,
            model.SETT_MEM_DISPLAY_TYPE,
        )
        new_combo(
            self,
            4,
            4,
            "LCD contrast",
            self._var_lcd_contrast,
            model.SETT_LCD_CONTRAST,
        )

        new_combo(
            self, 5, 0, "AM Antenna", self._var_am_ant, model.SETT_AM_ANT
        )
        new_combo(
            self, 5, 2, "FM Antenna", self._var_fm_ant, model.SETT_FM_ANT
        )

        new_checkbox(self, 6, 0, "AM AF filter", self._var_af_filer_am)
        new_checkbox(self, 6, 2, "FM AF filter", self._var_af_filer_fm)
        new_checkbox(self, 6, 4, "WFM AF filter", self._var_af_filer_wfm)

        new_combo(
            self,
            7,
            0,
            "Charge type",
            self._var_charging_type,
            model.SETT_CHARGE_TYPE,
        )

        new_checkbox(self, 8, 0, "Set expand", self._var_set_expand)

        new_checkbox(
            self, 9, 0, "Program skip scan", self._var_program_skip_scan
        )
        new_combo(
            self,
            9,
            2,
            "Scan pause timer",
            self._var_pause_timer,
            model.SETT_PAUSE_TIMER,
        )
        new_combo(
            self,
            9,
            4,
            "Scan resume timer",
            self._var_resume_timer,
            model.SETT_RESUME_TIMER,
        )
        new_checkbox(self, 10, 0, "Scan stop beep", self._var_stop_beep)

        tk.Label(self, text="Bank links:").grid(
            row=11, column=0, sticky=tk.N + tk.W, padx=6, pady=6
        )
        for idx, bank in enumerate(model.BANK_NAMES):
            # TODO: bank links names?
            new_checkbox(
                self, 12 + idx // 6, idx % 6, bank, self._var_bank_links[idx]
            )

        new_combo(
            self,
            16,
            0,
            "CIV baud rate",
            self._var_civ_baud_rate,
            model.SETT_CIV_BAUD_RATE,
        )
        new_entry(self, 16, 2, "CIV address", self._var_civ_address)
        new_checkbox(self, 16, 4, "CIV transceive", self._var_civ_transceive)

    def __fill(self) -> None:
        sett = self._radio_memory.get_settings()
        ic(sett)
        self._var_func_dial_step.set(
            model.SETT_FUNC_DIAL_STEP[sett.func_dial_step]
        )
        self._var_key_beep.set(1 if sett.key_beep else 0)
        self._var_beep_level.set(model.SETT_BEEP_LEVEL[sett.beep_level])
        self._var_backlight.set(model.SETT_BACKLIGHT[sett.backlight])
        self._var_power_save.set(1 if sett.power_save else 0)
        self._var_am_ant.set(model.SETT_AM_ANT[sett.am_ant])
        self._var_fm_ant.set(model.SETT_FM_ANT[sett.fm_ant])
        self._var_civ_address.set(str(sett.civ_address))  # TODO: hex
        self._var_civ_baud_rate.set(
            model.SETT_CIV_BAUD_RATE[sett.civ_baud_rate]
        )
        self._var_civ_transceive.set(1 if sett.civ_transceive else 0)
        self._var_dial_function.set(
            model.SETT_DIAL_FUNCTION[sett.dial_function]
        )
        self._var_mem_display_type.set(
            model.SETT_MEM_DISPLAY_TYPE[sett.mem_display_type]
        )
        self._var_program_skip_scan.set(1 if sett.program_skip_scan else 0)
        self._var_pause_timer.set(model.SETT_PAUSE_TIMER[sett.pause_timer])
        self._var_resume_timer.set(model.SETT_RESUME_TIMER[sett.resume_timer])
        self._var_stop_beep.set(1 if sett.stop_beep else 0)
        self._var_set_expand.set(1 if sett.set_expand else 0)
        self._var_key_lock.set(model.SETT_KEY_LOCK[sett.key_lock])
        self._var_dial_speed_up.set(1 if sett.dial_speed_up else 0)
        self._var_monitor.set(model.SETT_MONITOR[sett.monitor])
        self._var_auto_power_off.set(1 if sett.auto_power_off else 0)
        self._var_lcd_contrast.set(model.SETT_LCD_CONTRAST[sett.lcd_contrast])
        self._var_af_filer_fm.set(1 if sett.af_filer_fm else 0)
        self._var_af_filer_wfm.set(1 if sett.af_filer_wfm else 0)
        self._var_af_filer_am.set(1 if sett.af_filer_am else 0)
        self._var_charging_type.set(model.SETT_CHARGE_TYPE[sett.charging_type])

        bl = sett.bank_links
        for blvar in reversed(self._var_bank_links):
            blvar.set(bl & 1)
            bl >>= 1

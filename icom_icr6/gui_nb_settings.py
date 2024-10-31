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
        self._var_func_dial_step = gui_model.ListVar(model.SETT_FUNC_DIAL_STEP)
        self._var_key_beep = gui_model.BoolVar()
        self._var_beep_level = gui_model.ListVar(model.SETT_BEEP_LEVEL)
        self._var_backlight = gui_model.ListVar(model.SETT_BACKLIGHT)
        self._var_power_save = gui_model.BoolVar()
        self._var_am_ant = gui_model.ListVar(model.SETT_AM_ANT)
        self._var_fm_ant = gui_model.ListVar(model.SETT_FM_ANT)
        self._var_civ_address = tk.StringVar()
        self._var_civ_baud_rate = gui_model.ListVar(model.SETT_CIV_BAUD_RATE)
        self._var_civ_transceive = gui_model.BoolVar()
        self._var_dial_function = gui_model.ListVar(model.SETT_DIAL_FUNCTION)
        self._var_mem_display_type = gui_model.ListVar(
            model.SETT_MEM_DISPLAY_TYPE
        )
        self._var_program_skip_scan = gui_model.BoolVar()
        self._var_bank_links = [tk.IntVar() for _ in range(22)]
        self._var_pause_timer = gui_model.ListVar(model.SETT_PAUSE_TIMER)
        self._var_resume_timer = gui_model.ListVar(model.SETT_RESUME_TIMER)
        self._var_stop_beep = gui_model.BoolVar()
        self._var_set_expand = gui_model.BoolVar()
        self._var_key_lock = gui_model.ListVar(model.SETT_KEY_LOCK)
        self._var_dial_speed_up = gui_model.BoolVar()
        self._var_monitor = gui_model.ListVar(model.SETT_MONITOR)
        self._var_auto_power_off = gui_model.BoolVar()
        self._var_lcd_contrast = gui_model.ListVar(model.SETT_LCD_CONTRAST)
        self._var_af_filer_fm = gui_model.BoolVar()
        self._var_af_filer_wfm = gui_model.BoolVar()
        self._var_af_filer_am = gui_model.BoolVar()
        self._var_charging_type = gui_model.ListVar(model.SETT_CHARGE_TYPE)

    def _create_fields(self) -> None:
        new_combo(
            self,
            0,
            0,
            "Func + Down/Up",
            self._var_func_dial_step,
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

        ttk.Button(self, text="Update", command=self.__on_update).grid(
            row=17, column=0, sticky=tk.E
        )

    def __fill(self) -> None:
        sett = self._radio_memory.get_settings()
        ic(sett)

        self._var_func_dial_step.set_raw(sett.func_dial_step)
        self._var_key_beep.set_raw(sett.key_beep)
        self._var_beep_level.set_raw(sett.beep_level)
        self._var_backlight.set_raw(sett.backlight)
        self._var_power_save.set_raw(sett.power_save)
        self._var_am_ant.set_raw(sett.am_ant)
        self._var_fm_ant.set_raw(sett.fm_ant)
        self._var_civ_address.set(f"{sett.civ_address:0x}")
        self._var_civ_baud_rate.set_raw(sett.civ_baud_rate)
        self._var_civ_transceive.set_raw(sett.civ_transceive)
        self._var_dial_function.set_raw(sett.dial_function)
        self._var_mem_display_type.set_raw(sett.mem_display_type)
        self._var_program_skip_scan.set_raw(sett.program_skip_scan)
        self._var_pause_timer.set_raw(sett.pause_timer)
        self._var_resume_timer.set_raw(sett.resume_timer)
        self._var_stop_beep.set(sett.stop_beep)
        self._var_set_expand.set_raw(sett.set_expand)
        self._var_key_lock.set_raw(sett.key_lock)
        self._var_dial_speed_up.set_raw(sett.dial_speed_up)
        self._var_monitor.set_raw(sett.monitor)
        self._var_auto_power_off.set_raw(sett.auto_power_off)
        self._var_lcd_contrast.set_raw(sett.lcd_contrast)
        self._var_af_filer_fm.set_raw(sett.af_filer_fm)
        self._var_af_filer_wfm.set_raw(sett.af_filer_wfm)
        self._var_af_filer_am.set_raw(sett.af_filer_am)
        self._var_charging_type.set_raw(sett.charging_type)

        bl = self._radio_memory.get_bank_links()
        for blvar, val in zip(self._var_bank_links, bl.bits(), strict=True):
            blvar.set(val)

    def __on_update(self) -> None:
        sett = self._radio_memory.get_settings()

        sett.func_dial_step = self._var_func_dial_step.get_raw()
        sett.key_beep = self._var_key_beep.get_raw()
        sett.beep_level = self._var_beep_level.get_raw()
        sett.backlight = self._var_backlight.get_raw()
        sett.power_save = self._var_power_save.get_raw()
        sett.am_ant = self._var_am_ant.get_raw()
        sett.fm_ant = self._var_fm_ant.get_raw()
        if add := self._var_civ_address.get():
            sett.civ_address = int(add, 16) & 0xFF

        sett.civ_baud_rate = self._var_civ_baud_rate.get_raw()
        sett.civ_transceive = self._var_civ_transceive.get_raw()
        sett.dial_function = self._var_dial_function.get_raw()
        sett.mem_display_type = self._var_mem_display_type.get_raw()
        sett.program_skip_scan = self._var_program_skip_scan.get_raw()
        sett.pause_timer = self._var_pause_timer.get_raw()
        sett.resume_timer = self._var_resume_timer.get_raw()
        sett.stop_beep = self._var_stop_beep.get_raw()
        sett.set_expand = self._var_set_expand.get_raw()
        sett.key_lock = self._var_key_lock.get_raw()
        sett.dial_speed_up = self._var_dial_speed_up.get_raw()
        sett.monitor = self._var_monitor.get_raw()
        sett.auto_power_off = self._var_auto_power_off.get_raw()
        sett.lcd_contrast = self._var_lcd_contrast.get_raw()
        sett.af_filer_fm = self._var_af_filer_fm.get_raw()
        sett.af_filer_wfm = self._var_af_filer_wfm.get_raw()
        sett.af_filer_am = self._var_af_filer_am.get_raw()
        sett.charging_type = self._var_charging_type.get_raw()

        self._radio_memory.set_settings(sett)

        bl = self._radio_memory.get_bank_links()
        for idx, blvar in enumerate(self._var_bank_links):
            bl[idx] = blvar.get() == 1

        self._radio_memory.set_bank_links(bl)

        self.__fill()

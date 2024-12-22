# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
from tkinter import ttk

from . import consts, gui_model, validators
from .change_manager import ChangeManeger
from .gui_widgets import new_checkbox, new_combo, new_entry
from .radio_memory import RadioMemory

_LOG = logging.getLogger(__name__)


class SettingsPage(tk.Frame):
    def __init__(self, parent: tk.Widget, cm: ChangeManeger) -> None:
        self._wx_frame: tk.Widget | None = None

        super().__init__(parent)

        self._change_manager = cm
        self._create_vars()
        self._create_fields()

    def update_tab(self) -> None:
        self.__update()

    @property
    def _radio_memory(self) -> RadioMemory:
        return self._change_manager.rm

    def _create_vars(self) -> None:
        self._var_func_dial_step = gui_model.ListVar(
            consts.SETT_FUNC_DIAL_STEP
        )
        self._var_key_beep = gui_model.BoolVar()
        self._var_beep_level = gui_model.ListVar(consts.SETT_BEEP_LEVEL)
        self._var_backlight = gui_model.ListVar(consts.SETT_BACKLIGHT)
        self._var_power_save = gui_model.BoolVar()
        self._var_am_ant = gui_model.ListVar(consts.SETT_AM_ANT)
        self._var_fm_ant = gui_model.ListVar(consts.SETT_FM_ANT)
        self._var_civ_address = tk.StringVar()
        self._var_civ_baud_rate = gui_model.ListVar(consts.SETT_CIV_BAUD_RATE)
        self._var_civ_transceive = gui_model.BoolVar()
        self._var_dial_function = gui_model.ListVar(consts.SETT_DIAL_FUNCTION)
        self._var_mem_display_type = gui_model.ListVar(
            consts.SETT_MEM_DISPLAY_TYPE
        )
        self._var_program_skip_scan = gui_model.BoolVar()
        self._var_pause_timer = gui_model.ListVar(consts.SETT_PAUSE_TIMER)
        self._var_resume_timer = gui_model.ListVar(consts.SETT_RESUME_TIMER)
        self._var_stop_beep = gui_model.BoolVar()
        self._var_set_expand = gui_model.BoolVar()
        self._var_key_lock = gui_model.ListVar(consts.SETT_KEY_LOCK)
        self._var_dial_speed_up = gui_model.BoolVar()
        self._var_monitor = gui_model.ListVar(consts.SETT_MONITOR)
        self._var_auto_power_off = gui_model.BoolVar()
        self._var_lcd_contrast = gui_model.ListVar(consts.SETT_LCD_CONTRAST)
        self._var_af_filer_fm = gui_model.BoolVar()
        self._var_af_filer_wfm = gui_model.BoolVar()
        self._var_af_filer_am = gui_model.BoolVar()
        self._var_charging_type = gui_model.ListVar(consts.SETT_CHARGER_TYPE)
        self._var_wx_alert = gui_model.BoolVar()
        self._var_wx_channel = gui_model.ListVar(consts.WX_CHANNELS)

        self._var_comment = tk.StringVar()

    def _create_fields(self) -> None:
        frame = tk.Frame(self)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)

        sframe = tk.Frame(frame)
        self._create_set_mode(sframe).pack(
            side=tk.TOP, expand=False, fill=tk.BOTH, padx=12, pady=12
        )
        self._create_sound(sframe).pack(
            side=tk.TOP, expand=False, fill=tk.BOTH, padx=12, pady=12
        )
        self._create_scan(sframe).pack(
            side=tk.TOP, expand=False, fill=tk.BOTH, padx=12, pady=12
        )
        sframe.grid(row=0, column=0, sticky=tk.W + tk.N + tk.W + tk.S)

        sframe = tk.Frame(frame)
        self._create_display(sframe).pack(
            side=tk.TOP, expand=False, fill=tk.BOTH, padx=12, pady=12
        )
        self._create_power(sframe).pack(
            side=tk.TOP, expand=False, fill=tk.BOTH, padx=12, pady=12
        )
        self._create_antenna(sframe).pack(
            side=tk.TOP, expand=False, fill=tk.BOTH, padx=12, pady=12
        )
        self._create_affilter(sframe).pack(
            side=tk.TOP, expand=False, fill=tk.BOTH, padx=12, pady=12
        )

        sframe.grid(row=0, column=1, sticky=tk.W + tk.N + tk.W + tk.S)

        self._right_frame = sframe = tk.Frame(frame)
        self._create_civ(sframe).pack(
            side=tk.TOP, expand=False, fill=tk.BOTH, padx=12, pady=12
        )
        self._create_radio(sframe).pack(
            side=tk.TOP, expand=False, fill=tk.BOTH, padx=12, pady=12
        )
        sframe.grid(row=0, column=2, sticky=tk.W + tk.N + tk.W + tk.S)

        frame.pack(fill=tk.X, side=tk.TOP, padx=12, pady=12)

        frame_btns = tk.Frame(self)
        frame_btns.columnconfigure(0, weight=1)
        ttk.Button(
            frame_btns, text="Save settings", command=self.__on_update
        ).grid(row=0, column=0, sticky=tk.E + tk.N)

        frame_btns.pack(side=tk.TOP, fill=tk.X, padx=12, pady=12)

    def _create_set_mode(self, parent: tk.Frame) -> tk.Widget:
        frame = ttk.LabelFrame(parent, text="Set/Mode")
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)

        new_combo(
            frame,
            0,
            0,
            "Func + Down/Up",
            self._var_func_dial_step,
            consts.SETT_FUNC_DIAL_STEP,
        )
        new_combo(
            frame,
            1,
            0,
            "Dial function",
            self._var_dial_function,
            consts.SETT_DIAL_FUNCTION,
        )

        new_checkbox(
            frame, 2, 0, "Dial speed up", self._var_dial_speed_up, colspan=2
        )

        new_combo(
            frame, 3, 0, "Monitor", self._var_monitor, consts.SETT_MONITOR
        )

        return frame

    def _create_power(self, parent: tk.Frame) -> tk.Widget:
        frame = ttk.LabelFrame(parent, text="Power")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        new_checkbox(frame, 0, 0, "Auto power save", self._var_power_save)
        new_checkbox(frame, 0, 1, "Auto power off", self._var_auto_power_off)

        return frame

    def _create_display(self, parent: tk.Frame) -> tk.Widget:
        frame = ttk.LabelFrame(parent, text="Display")
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)

        new_combo(
            frame,
            0,
            0,
            "Backlight",
            self._var_backlight,
            consts.SETT_BACKLIGHT,
        )
        new_combo(
            frame,
            1,
            0,
            "Memory display type",
            self._var_mem_display_type,
            consts.SETT_MEM_DISPLAY_TYPE,
        )
        new_combo(
            frame,
            2,
            0,
            "LCD contrast",
            self._var_lcd_contrast,
            consts.SETT_LCD_CONTRAST,
        )

        return frame

    def _create_antenna(self, parent: tk.Frame) -> tk.Widget:
        frame = ttk.LabelFrame(parent, text="Antenna")
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)

        new_combo(
            frame, 0, 0, "AM Antenna", self._var_am_ant, consts.SETT_AM_ANT
        )
        new_combo(
            frame, 1, 0, "FM Antenna", self._var_fm_ant, consts.SETT_FM_ANT
        )

        return frame

    def _create_affilter(self, parent: tk.Frame) -> tk.Widget:
        frame = ttk.LabelFrame(parent, text="AF Filter")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)

        new_checkbox(frame, 0, 0, "AM", self._var_af_filer_am)
        new_checkbox(frame, 0, 1, "FM", self._var_af_filer_fm)
        new_checkbox(frame, 0, 2, "WFM", self._var_af_filer_wfm)

        return frame

    def _create_scan(self, parent: tk.Frame) -> tk.Widget:
        frame = ttk.LabelFrame(parent, text="Scan")
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)

        new_checkbox(
            frame,
            0,
            0,
            "Program skip scan",
            self._var_program_skip_scan,
        )
        new_checkbox(frame, 0, 1, "Scan stop beep", self._var_stop_beep)
        new_combo(
            frame,
            1,
            0,
            "Scan pause timer",
            self._var_pause_timer,
            consts.SETT_PAUSE_TIMER,
        )
        new_combo(
            frame,
            2,
            0,
            "Scan resume timer",
            self._var_resume_timer,
            consts.SETT_RESUME_TIMER,
        )
        return frame

    def _create_civ(self, parent: tk.Frame) -> tk.Widget:
        frame = ttk.LabelFrame(parent, text="CI-V")
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)

        new_combo(
            frame,
            0,
            0,
            "CIV baud rate",
            self._var_civ_baud_rate,
            consts.SETT_CIV_BAUD_RATE,
        )
        new_entry(frame, 1, 0, "CIV address", self._var_civ_address)
        new_checkbox(
            frame, 2, 0, "CIV transceive", self._var_civ_transceive, colspan=2
        )

        return frame

    def _create_sound(self, parent: tk.Frame) -> tk.Widget:
        frame = ttk.LabelFrame(parent, text="Sounds")
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)

        new_checkbox(frame, 0, 0, "Key beep", self._var_key_beep, colspan=2)
        new_combo(
            frame,
            1,
            0,
            "Beep level",
            self._var_beep_level,
            consts.SETT_BEEP_LEVEL,
        )

        return frame

    def _create_radio(self, parent: tk.Frame) -> tk.Widget:
        frame = ttk.LabelFrame(parent, text="Radio")
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)

        new_combo(
            frame, 0, 0, "Key lock", self._var_key_lock, consts.SETT_KEY_LOCK
        )

        new_combo(
            frame,
            1,
            0,
            "Charge type",
            self._var_charging_type,
            consts.SETT_CHARGER_TYPE,
            colspan=3,
        )

        new_checkbox(frame, 2, 0, "Set expand", self._var_set_expand)

        validator = self.register(validate_comment)
        new_entry(
            frame, 3, 0, "Comment", self._var_comment, validator=validator
        )

        return frame

    def _create_wx(self) -> None:
        if self._wx_frame is not None:
            return

        parent = self._right_frame

        self._wx_frame = frame = ttk.LabelFrame(parent, text="WX")
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)

        new_checkbox(
            frame,
            0,
            0,
            "WX alert",
            self._var_wx_alert,
            colspan=2,
        )
        new_combo(
            frame,
            1,
            0,
            "WX channel",
            self._var_wx_channel,
            consts.WX_CHANNELS,
            colspan=3,
        )
        frame.pack(side=tk.TOP, expand=False, fill=tk.BOTH, padx=12, pady=12)

    def __update(self) -> None:
        sett = self._radio_memory.settings

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

        if self._radio_memory.is_usa_model():
            self._create_wx()
            self._var_wx_alert.set(sett.wx_alert)
            self._var_wx_channel.set_raw(sett.wx_channel)
        elif self._wx_frame:
            self._wx_frame.destroy()
            self._wx_frame = None

        self._var_comment.set(self._radio_memory.comment)

    def __on_update(self) -> None:
        sett = self._radio_memory.settings.clone()

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

        if self._radio_memory.is_usa_model():
            sett.wx_alert = self._var_wx_alert.get_raw()
            sett.wx_channel = self._var_wx_channel.get_raw()

        self._change_manager.set_settings(sett)
        self._change_manager.set_comment(self._var_comment.get())
        self._change_manager.commit()

        self.__update()


def validate_comment(comment: str) -> bool:
    if not comment:
        return True

    try:
        validators.validate_comment(comment)
    except ValueError:
        return False

    return True

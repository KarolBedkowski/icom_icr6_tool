# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from pathlib import Path
from tkinter import messagebox, ttk

from icom_icr6 import config, consts, expimp, fixers, ic_io, model
from icom_icr6.change_manager import ChangeManeger
from icom_icr6.radio_memory import RadioMemory

from . import gui_model, scanedges_list

_LOG = logging.getLogger(__name__)


class ControlPage(tk.Frame):
    def __init__(self, parent: tk.Widget, cm: ChangeManeger) -> None:
        super().__init__(parent)
        self._change_manager = cm
        self._radio: ic_io.Radio | None = None
        self._commands: ic_io.Commands | None = None
        self._create_vars()
        self._create_body()

    def update_tab(self) -> None:
        pass

    def reset(self) -> None:
        pass

    @property
    def _radio_memory(self) -> RadioMemory:
        return self._change_manager.rm

    def _create_vars(self) -> None:
        self._var_port = tk.StringVar()
        self._var_freq = tk.StringVar()
        self._var_freq.trace("w", self._on_set_freq)
        self._var_mode = tk.StringVar()
        self._var_attenuator = tk.IntVar()
        self._var_affilter = tk.IntVar()
        self._var_vcs = tk.IntVar()
        self._var_volume = tk.IntVar()
        self._var_squelch = tk.IntVar()
        self._var_label_volume = tk.StringVar()
        self._var_label_volume.set("xxxxx")
        self._var_label_squelch = tk.StringVar()
        self._var_label_squelch.set("xxxxxx")

    def _create_body(self) -> None:
        # freq
        # mode
        # attenuator
        # antenna
        # volume
        # squelch
        # smeter
        # tsql mode / freq
        # dtcs mode / freq
        # vcs
        # receiver id
        # af filter

        frame = tk.Frame(self)
        self._create_body_port(frame).pack(
            side=tk.TOP, fill=tk.X, padx=12, pady=12
        )
        self._create_body_freq(frame).pack(
            side=tk.TOP, fill=tk.X, padx=12, pady=12
        )
        self._create_body_mode(frame).pack(
            side=tk.TOP, fill=tk.X, padx=12, pady=12
        )
        self._create_body_opt(frame).pack(
            side=tk.TOP, fill=tk.X, padx=12, pady=12
        )
        self._create_body_vol(frame).pack(
            side=tk.TOP, fill=tk.X, padx=12, pady=12
        )
        self._create_body_squelch(frame).pack(
            side=tk.TOP, fill=tk.X, padx=12, pady=12
        )

        frame.pack()

    def _create_body_port(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent)
        ttk.Label(frame, text="Port: ").pack(side=tk.LEFT, padx=6, pady=6)
        ttys = [
            str(p) for p in Path("/dev/").iterdir() if p.name.startswith("tty")
        ]

        self._var_port.set(config.CONFIG.last_port)
        ttk.Combobox(
            frame,
            values=ttys,
            exportselection=False,
            textvariable=self._var_port,
        ).pack(side=tk.LEFT, expand=True, padx=6, pady=6)

        self._btn_connect = ttk.Button(
            frame,
            text="Connect",
            width=10,
            command=self._on_connect_button,
            default=tk.ACTIVE,
        )
        self._btn_connect.pack(side=tk.RIGHT, padx=5, pady=5)

        return frame

    def _create_body_freq(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent)

        ttk.Label(frame, text="Frequency: ").pack(side=tk.LEFT)

        freq = ttk.Entry(frame, textvariable=self._var_freq)
        freq.pack(side=tk.LEFT, padx=12, pady=6)

        return frame

    def _create_body_mode(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent)

        ttk.Label(frame, text="Mode: ").pack(side=tk.LEFT)

        for mode in ("FM", "WFM", "AM"):
            ttk.Radiobutton(
                frame,
                text=mode,
                variable=self._var_mode,
                command=self._on_set_mode,
                value=mode,
            ).pack(side=tk.LEFT, padx=12)

        return frame

    def _create_body_opt(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent)

        ttk.Checkbutton(
            frame,
            text="Attenuator",
            variable=self._var_attenuator,
            onvalue=1,
            offvalue=0,
            command=self._on_set_attenuator,
        ).pack(side=tk.LEFT, padx=12)

        ttk.Checkbutton(
            frame,
            text="AF filter",
            variable=self._var_affilter,
            onvalue=1,
            offvalue=0,
            command=self._on_set_affilter,
        ).pack(side=tk.LEFT, padx=12)

        ttk.Checkbutton(
            frame,
            text="VCS",
            variable=self._var_vcs,
            onvalue=1,
            offvalue=0,
            command=self._on_set_vcs,
        ).pack(side=tk.LEFT, padx=12)

        return frame

    def _create_body_vol(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent)

        ttk.Label(frame, text="Volume: ").pack(side=tk.LEFT)
        ttk.Scale(
            frame,
            from_=0,
            to=len(consts.MONITOR_VOLUME_STEPS) - 1,
            variable=self._var_volume,
            command=self._on_set_volume,
        ).pack(side=tk.LEFT, padx=12)
        ttk.Label(frame, textvariable=self._var_label_volume).pack(
            side=tk.LEFT
        )

        return frame

    def _create_body_squelch(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent)

        ttk.Label(frame, text="Squelch: ").pack(side=tk.LEFT)
        ttk.Scale(
            frame,
            from_=0,
            to=len(consts.MONITOR_SQUELCH_STEPS) - 1,
            variable=self._var_squelch,
            command=self._on_set_squelch,
        ).pack(side=tk.LEFT, padx=12)
        ttk.Label(frame, textvariable=self._var_label_squelch).pack(
            side=tk.LEFT
        )

        return frame

    def _load_data(self) -> None:
        if not self._commands:
            return

        status = self._commands.get_status()
        _LOG.debug("status: %r", status)
        if not status:
            return

        self._var_freq.set(model.fmt.format_freq(status.frequency))
        self._var_mode.set(consts.MODES[status.mode])
        self._var_affilter.set(1 if status.affilter else 0)
        self._var_attenuator.set(1 if status.attenuator else 0)
        self._var_vcs.set(1 if status.vcs else 0)
        self._var_vcs.set(1 if status.vcs else 0)
        self._var_squelch.set(status.squelch)
        self._var_volume.set(status.volume)
        self._var_label_volume.set(str(status.volume))
        self._var_label_squelch.set(
            consts.MONITOR_SQUELCH_LEVEL[status.squelch]
        )

    def _on_connect_button(self) -> None:
        self._radio = ic_io.Radio(self._var_port.get())
        self._commands = ic_io.Commands(self._radio)
        self._load_data()

    def _on_set_freq(self, _var: str, _idx: str, _op: str) -> None:
        if self._commands:
            freq = model.fmt.parse_freq(self._var_freq.get())
            _LOG.debug("freq: %r", freq)
            self._commands.set_frequency(freq)

    def _on_set_mode(self) -> None:
        if self._commands:
            mode = self._var_mode.get()
            mode_id = consts.MODES.index(mode)
            self._commands.set_mode(mode_id)

    def _on_set_affilter(self) -> None:
        if self._commands:
            self._commands.set_affilter(self._var_affilter.get() == 1)

    def _on_set_attenuator(self) -> None:
        if self._commands:
            self._commands.set_attenuator(self._var_attenuator.get() == 1)

    def _on_set_vcs(self) -> None:
        if self._commands:
            self._commands.set_vcs(self._var_vcs.get() == 1)

    def _on_set_squelch(self, _arg: str) -> None:
        sql = self._var_squelch.get()
        self._var_label_squelch.set(consts.MONITOR_SQUELCH_LEVEL[sql])
        if self._commands:
            self._commands.set_squelch(sql)

    def _on_set_volume(self, _arg: str) -> None:
        volume = self._var_volume.get()
        self._var_label_volume.set(str(volume))
        if self._commands:
            self._commands.set_squelch(volume)

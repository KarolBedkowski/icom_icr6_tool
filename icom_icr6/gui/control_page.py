# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from pathlib import Path
from tkinter import font, messagebox, ttk

from icom_icr6 import config, consts, fixers, ic_io, model, validators
from icom_icr6.change_manager import ChangeManeger
from icom_icr6.radio_memory import RadioMemory

_ = ty
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
        self._var_label_volume.set("        ")
        self._var_label_squelch = tk.StringVar()
        self._var_label_squelch.set("        ")
        self._var_step = tk.StringVar()
        self._var_step.set("10")
        self._var_tone = tk.StringVar()
        self._var_tsql = tk.StringVar()
        self._var_dtcs = tk.StringVar()
        self._var_polarity = tk.IntVar()

    def _create_body(self) -> None:
        # antenna
        # smeter
        # tsql mode / freq
        # dtcs mode / freq
        # receiver id

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
        self._create_body_tone(frame).pack(
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

        self._btn_refresh = ttk.Button(
            frame,
            text="Refresh",
            width=10,
            command=self._on_refresh_button,
            default=tk.ACTIVE,
            state="disabled",
        )
        self._btn_refresh.pack(side=tk.RIGHT, padx=5, pady=5)

        self._btn_connect = ttk.Button(
            frame,
            text="Connect",
            width=10,
            command=self._on_connect_button,
            default=tk.ACTIVE,
        )
        self._btn_connect.pack(side=tk.RIGHT, padx=5, pady=5)

        return frame

    def _create_body_freq(self, parent: tk.Frame) -> tk.Widget:
        frame = tk.LabelFrame(parent, text="Frequency")

        validator = self.register(validate_freq)
        freq = ttk.Entry(
            frame,
            textvariable=self._var_freq,
            font=font.Font(size=20),
            width=12,
            validate="all",
            validatecommand=(validator, "%P"),
        )
        freq.pack(side=tk.TOP, padx=12, pady=6)

        sframe = tk.Frame(frame)

        ttk.Label(sframe, text="Step: ").pack(side=tk.LEFT)

        ttk.Combobox(
            sframe,
            textvariable=self._var_step,
            exportselection=False,
            state="readonly",
            values=consts.STEPS[:-2],
            width=4,
        ).pack(side=tk.LEFT, padx=6, expand=False)

        ttk.Button(
            sframe,
            text="Down",
            width=10,
            command=self._on_freq_down,
            default=tk.ACTIVE,
        ).pack(side=tk.RIGHT, padx=5, pady=5)

        ttk.Button(
            sframe,
            text="Up",
            width=10,
            command=self._on_freq_up,
            default=tk.ACTIVE,
        ).pack(side=tk.RIGHT, padx=5, pady=5)

        sframe.pack(side=tk.TOP, padx=12, pady=6)

        return frame

    def _create_body_mode(self, parent: tk.Frame) -> tk.Widget:
        frame = tk.LabelFrame(parent, text="Mode")

        for mode in ("FM", "WFM", "AM"):
            ttk.Radiobutton(
                frame,
                text=mode,
                variable=self._var_mode,
                command=self._on_set_mode,
                value=mode,
            ).pack(side=tk.LEFT, padx=12, pady=6)

        return frame

    def _create_body_opt(self, parent: tk.Frame) -> tk.Widget:
        frame = tk.LabelFrame(parent, text="Options")

        ttk.Checkbutton(
            frame,
            text="Attenuator",
            variable=self._var_attenuator,
            onvalue=1,
            offvalue=0,
            command=self._on_set_attenuator,
        ).pack(side=tk.LEFT, padx=12, pady=6)

        ttk.Checkbutton(
            frame,
            text="AF filter",
            variable=self._var_affilter,
            onvalue=1,
            offvalue=0,
            command=self._on_set_affilter,
        ).pack(side=tk.LEFT, padx=12, pady=6)

        ttk.Checkbutton(
            frame,
            text="VCS",
            variable=self._var_vcs,
            onvalue=1,
            offvalue=0,
            command=self._on_set_vcs,
        ).pack(side=tk.LEFT, padx=12, pady=6)

        return frame

    def _create_body_vol(self, parent: tk.Frame) -> tk.Widget:
        frame = ttk.LabelFrame(parent)

        ttk.Label(frame, text="Volume: ").grid(
            row=0, column=0, stick=tk.W, padx=6, pady=6
        )
        ttk.Scale(
            frame,
            from_=0,
            to=len(consts.MONITOR_VOLUME_STEPS) - 1,
            variable=self._var_volume,
            command=self._on_set_volume,
            length=300,
        ).grid(row=0, column=1, stick=tk.W, padx=6, pady=6)
        ttk.Label(frame, textvariable=self._var_label_volume).grid(
            row=0, column=2, stick=tk.W, padx=6, pady=6
        )

        ttk.Label(frame, text="Squelch: ").grid(
            row=1, column=0, stick=tk.W, padx=6, pady=6
        )
        ttk.Scale(
            frame,
            from_=0,
            to=len(consts.MONITOR_SQUELCH_STEPS) - 1,
            variable=self._var_squelch,
            command=self._on_set_squelch,
            length=300,
        ).grid(row=1, column=1, stick=tk.W, padx=6, pady=6)
        ttk.Label(frame, textvariable=self._var_label_squelch).grid(
            row=1, column=2, stick=tk.W, padx=6, pady=6
        )

        return frame

    def _create_body_tone(self, parent: tk.Frame) -> tk.Widget:
        frame = tk.LabelFrame(parent)

        sframe = tk.Frame(frame)
        ttk.Label(sframe, text="Tone: ").pack(side=tk.LEFT)
        ttk.Combobox(
            sframe,
            textvariable=self._var_tone,
            exportselection=False,
            state="readonly",
            values=consts.TONE_MODES,
            postcommand=self._on_change_tone,
        ).pack(side=tk.LEFT, padx=6, expand=False)
        sframe.pack(side=tk.TOP, pady=6, fill=tk.X, padx=6)

        # round to one digit after comma
        tones = [
            f"{float(t.replace(',', '.')):0.1f}".replace(".", ",")
            for t in consts.CTCSS_TONES
        ]

        sframe = tk.Frame(frame)
        ttk.Label(sframe, text="TSQL: ").pack(side=tk.LEFT)
        ttk.Combobox(
            sframe,
            textvariable=self._var_tsql,
            exportselection=False,
            state="readonly",
            values=tones,
            postcommand=self._on_change_tone,
        ).pack(side=tk.LEFT, padx=6, expand=False)
        sframe.pack(side=tk.TOP, pady=6, fill=tk.X, padx=6)

        sframe = tk.Frame(frame)
        ttk.Label(sframe, text="DTCS: ").pack(side=tk.LEFT)
        ttk.Combobox(
            sframe,
            textvariable=self._var_dtcs,
            exportselection=False,
            state="readonly",
            values=consts.DTCS_CODES,
            postcommand=self._on_change_tone,
        ).pack(side=tk.LEFT, padx=6, expand=False, pady=6)

        ttk.Checkbutton(
            sframe,
            text="Polarity reverse",
            variable=self._var_polarity,
            onvalue=1,
            offvalue=0,
            command=self._on_change_tone,
        ).pack(side=tk.LEFT, padx=12)
        sframe.pack(side=tk.TOP, pady=6, fill=tk.X, padx=6)

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
        self._var_tone.set(consts.TONE_MODES[status.tone_mode])
        self._var_tsql.set(f"{status.tone / 10:0.1f}".replace(".", ","))
        self._var_dtcs.set(str(status.dtcs_code))
        self._var_polarity.set(status.dtcs_polarity)

    def _on_connect_button(self) -> None:
        if self._radio:
            # connected; disconnect
            self._radio = None
            self._commands = None
            self._btn_connect["text"] = "Connect"
            self._btn_refresh["state"] = "disabled"
            return

        try:
            self._radio = ic_io.Radio(self._var_port.get())
            self._commands = ic_io.DummyCommands(self._radio)
            self._load_data()
        except Exception as err:
            messagebox.showerror("Connect error", f"Error: {err}")
            self._radio = None
            self._commands = None
            return

        self._btn_refresh["state"] = "normal"
        self._btn_connect["text"] = "Disconnect"

    def _on_refresh_button(self) -> None:
        self._load_data()

    def _on_set_freq(self, _var: str, _idx: str, _op: str) -> None:
        if self._commands:
            freq = model.fmt.parse_freq(self._var_freq.get())
            freq = fixers.fix_frequency(freq)
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

    def _on_change_tone(self) -> None:
        if not self._commands:
            return

        tone = consts.TONE_MODES.index(self._var_tone.get())
        self._commands.set_tone_mode(tone)
        match tone:
            case 1 | 2:
                tsql = float(self._var_tsql.get().replace(",", ".")) * 10
                self._commands.set_tone_freq(int(tsql * 10))

            case 3 | 4:
                dtcs = int(self._var_dtcs.get())
                polarity = self._var_polarity.get()
                self._commands.set_dtsc(polarity, dtcs)

    def _on_freq_down(self) -> None:
        self._change_freq(-1)

    def _on_freq_up(self) -> None:
        self._change_freq(1)

    def _change_freq(self, direction: int) -> None:
        if not self._commands:
            return

        step = consts.STEPS_KHZ[consts.STEPS.index(self._var_step.get())]
        if direction < 0:
            step *= -1

        freq = model.fmt.parse_freq(self._var_freq.get())
        freq = int(freq + step)
        freq = fixers.fix_frequency(freq)
        self._commands.set_frequency(freq)
        # TODO: read from radio ?
        self._var_freq.set(model.fmt.format_freq(freq))


def validate_freq(freq: str) -> bool:
    try:
        nfreq = model.fmt.parse_freq(freq)

    except Exception:
        _LOG.exception("freq: %r", freq)
        return False

    return consts.MIN_FREQUENCY <= nfreq <= consts.MAX_FREQUENCY

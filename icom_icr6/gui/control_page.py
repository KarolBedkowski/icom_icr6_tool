# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
""" """

from __future__ import annotations

import logging
import tkinter as tk
import typing as ty
from pathlib import Path
from tkinter import font, messagebox, ttk

from icom_icr6 import config, consts, fixers, ic_io, model

if ty.TYPE_CHECKING:
    from icom_icr6.change_manager import ChangeManeger
    from icom_icr6.radio_memory import RadioMemory

_ = ty
_LOG = logging.getLogger(__name__)


T = ty.Callable[..., None]


def action_decor(method: T) -> T:
    """Action decorator that handle error and execute decorated function
    only when connection exists and not busy."""

    def func(self: ControlPage, *args: object, **kwargs: object) -> None:
        _LOG.debug("call %r(%r, %r) error", method, args, kwargs)

        if not self._commands or self._busy:
            return

        try:
            method(self, *args, **kwargs)
        except Exception as err:
            _LOG.exception("call %r(%r, %r) error", method, args, kwargs)
            messagebox.showerror("Connection error", f"Error: {err}")

    return func


class ControlPage(tk.Frame):
    def __init__(self, parent: tk.Widget, cm: ChangeManeger) -> None:
        super().__init__(parent)
        self._change_manager = cm
        self._radio: ic_io.Radio | None = None
        self._commands: ic_io.Commands | None = None
        self._busy = False
        self._create_vars()
        self._frames: list[tk.Widget] = []
        self._create_body()
        self._set_frames_state("disabled")

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
        self._var_goto_band = tk.StringVar()
        self._var_goto_channel = tk.StringVar()
        self._var_goto_bankchannel = tk.StringVar()
        self._var_goto_awchannel = tk.StringVar()

        self._last_volume = -1
        self._last_squelch = -1

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

        self._frames = [
            self._create_body_freq(frame),
            self._create_body_mode(frame),
            self._create_body_opt(frame),
            self._create_body_vol(frame),
            self._create_body_tone(frame),
            self._create_body_goto(frame),
        ]

        for f in self._frames:
            f.pack(side=tk.TOP, fill=tk.X, padx=12, pady=12)

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

    def _create_body_goto(self, parent: tk.Frame) -> tk.Widget:
        frame = ttk.LabelFrame(parent, text="Go to...")

        ttk.Label(frame, text="Band: ").grid(
            row=0, column=0, stick=tk.W, padx=6, pady=6
        )
        self._bands_combobox = ttk.Combobox(
            frame,
            textvariable=self._var_goto_band,
            state="readonly",
            values=[],
            width=30,
        )
        self._bands_combobox.grid(row=0, column=1, stick=tk.W, padx=6, pady=6)
        ttk.Button(
            frame,
            text="Goto",
            command=self._on_goto_band_button,
            default=tk.ACTIVE,
        ).grid(row=0, column=2, stick=tk.W, padx=6, pady=6)

        ttk.Label(frame, text="Channel: ").grid(
            row=1, column=0, stick=tk.W, padx=6, pady=6
        )
        self._channels_combobox = ttk.Combobox(
            frame,
            textvariable=self._var_goto_channel,
            state="readonly",
            values=[],
            width=30,
        )
        self._channels_combobox.grid(
            row=1, column=1, stick=tk.W, padx=6, pady=6
        )
        ttk.Button(
            frame,
            text="Goto",
            command=self._on_goto_channel_button,
            default=tk.ACTIVE,
        ).grid(row=1, column=2, stick=tk.W, padx=6, pady=6)

        ttk.Label(frame, text="Bank channel: ").grid(
            row=2, column=0, stick=tk.W, padx=6, pady=6
        )
        self._bankchannels_combobox = ttk.Combobox(
            frame,
            textvariable=self._var_goto_bankchannel,
            state="readonly",
            values=[],
            width=30,
        )
        self._bankchannels_combobox.grid(
            row=2, column=1, stick=tk.W, padx=6, pady=6
        )
        ttk.Button(
            frame,
            text="Goto",
            command=self._on_goto_bankchannel_button,
            default=tk.ACTIVE,
        ).grid(row=2, column=2, stick=tk.W, padx=6, pady=6)

        ttk.Label(frame, text="AW channel: ").grid(
            row=3, column=0, stick=tk.W, padx=6, pady=6
        )
        self._awchannels_combobox = ttk.Combobox(
            frame,
            textvariable=self._var_goto_awchannel,
            state="readonly",
            values=[],
            width=30,
        )
        self._awchannels_combobox.grid(
            row=3, column=1, stick=tk.W, padx=6, pady=6
        )
        ttk.Button(
            frame,
            text="Goto",
            command=self._on_goto_awchannel_button,
            default=tk.ACTIVE,
        ).grid(row=3, column=2, stick=tk.W, padx=6, pady=6)

        return frame

    def _load_data(self) -> None:
        _LOG.debug("_load_data")
        if not self._commands:
            return

        status = self._commands.get_status()
        _LOG.debug("status: %r", status)
        if not status:
            self._busy = False
            return

        self._var_freq.set(model.fmt.format_freq(status.frequency))
        self._var_mode.set(consts.MODES[status.mode])
        self._var_affilter.set(1 if status.affilter else 0)
        self._var_attenuator.set(1 if status.attenuator else 0)
        self._var_vcs.set(1 if status.vcs else 0)
        self._var_vcs.set(1 if status.vcs else 0)
        self._var_squelch.set(status.squelch)
        self._last_squelch = status.squelch
        self._var_volume.set(status.volume)
        self._last_volume = status.volume
        self._var_label_volume.set(str(status.volume))
        self._var_label_squelch.set(
            consts.MONITOR_SQUELCH_LEVEL[status.squelch]
        )
        self._var_tone.set(consts.TONE_MODES[status.tone_mode])
        self._var_tsql.set(f"{status.tone / 10:0.1f}".replace(".", ","))
        self._var_dtcs.set(str(status.dtcs_code))
        self._var_polarity.set(status.dtcs_polarity)

        rm = self._change_manager.rm
        self._bands_combobox["values"] = [
            f"{b.idx}:  {model.fmt.format_freq(b.freq)}" for b in rm.bands
        ]
        self._channels_combobox["values"] = [
            f"{c.number}:  {model.fmt.format_freq(c.freq)}  {c.name}"
            for c in rm.get_active_channels()
        ]
        self._awchannels_combobox["values"] = [
            f"{c.number}:  {model.fmt.format_freq(c.freq)}"
            for c in rm.awchannels
        ]

        bankchannels = [
            f"{consts.BANK_NAMES[c.bank]}/{c.bank_pos:>3}  {c.number}:  "
            f"{model.fmt.format_freq(c.freq)}  {c.name}"
            for c in rm.get_active_channels()
            if c.bank != consts.BANK_NOT_SET
        ]
        bankchannels.sort()
        self._bankchannels_combobox["values"] = bankchannels

    def _on_connect_button(self) -> None:
        if self._busy:
            return

        if self._radio:
            # connected; disconnect
            self._radio = None
            self._commands = None
            self._btn_connect["text"] = "Connect"
            self._btn_refresh["state"] = "disabled"
            self._set_frames_state("disabled")
            return

        self._busy = True
        port = self._var_port.get()
        try:
            self._radio = ic_io.Radio(port)
            self._commands = (
                ic_io.Commands(self._radio)
                if port
                else ic_io.DummyCommands(self._radio)
            )
            self._load_data()
        except Exception as err:
            self._radio = None
            self._commands = None
            self._set_frames_state("disabled")
            messagebox.showerror("Connect error", f"Error: {err}")
            self._busy = False
            return

        self._btn_refresh["state"] = "normal"
        self._btn_connect["text"] = "Disconnect"
        self._set_frames_state("normal")
        self._busy = False

    def _on_refresh_button(self) -> None:
        if self._busy:
            return

        self._busy = True
        try:
            self._load_data()
        except Exception:
            _LOG.exception("_on_refresh_button load data error")

        self._busy = False

    def _on_goto_band_button(self) -> None:
        if self._busy or not self._commands:
            return

        val = self._var_goto_band.get()
        if not val:
            return

        bandidx = int(val.partition(":")[0])
        band = self._change_manager.rm.bands[bandidx]
        self._var_freq.set(model.fmt.format_freq(band.freq))
        self._var_mode.set(consts.MODES[band.mode])

    def _on_goto_channel_button(self) -> None:
        if self._busy or not self._commands:
            return

        val = self._var_goto_channel.get()
        if not val:
            return

        number = int(val.partition(":")[0])
        channel = self._change_manager.rm.channels[number]
        self._var_freq.set(model.fmt.format_freq(channel.freq))
        self._var_mode.set(consts.MODES[channel.mode])

    def _on_goto_bankchannel_button(self) -> None:
        if self._busy or not self._commands:
            return

        val = self._var_goto_bankchannel.get()
        if not val:
            return

        number = int(val.partition(":")[0].rpartition(" ")[2])
        channel = self._change_manager.rm.channels[number]
        self._var_freq.set(model.fmt.format_freq(channel.freq))
        self._var_mode.set(consts.MODES[channel.mode])

    def _on_goto_awchannel_button(self) -> None:
        if self._busy or not self._commands:
            return

        val = self._var_goto_awchannel.get()
        if not val:
            return

        number = int(val.partition(":")[0])
        channel = self._change_manager.rm.awchannels[number]
        self._var_freq.set(model.fmt.format_freq(channel.freq))
        self._var_mode.set(consts.MODES[channel.mode])

    @action_decor
    def _on_set_freq(self, _var: str, _idx: str, _op: str) -> None:
        assert self._commands
        freq = model.fmt.parse_freq(self._var_freq.get())
        freq = fixers.fix_frequency(freq)
        self._commands.set_frequency(freq)

    @action_decor
    def _on_set_mode(self) -> None:
        assert self._commands
        mode = self._var_mode.get()
        mode_id = consts.MODES.index(mode)
        self._commands.set_mode(mode_id)

    @action_decor
    def _on_set_affilter(self) -> None:
        assert self._commands
        self._commands.set_affilter(self._var_affilter.get() == 1)

    @action_decor
    def _on_set_attenuator(self) -> None:
        assert self._commands
        self._commands.set_attenuator(self._var_attenuator.get() == 1)

    @action_decor
    def _on_set_vcs(self) -> None:
        assert self._commands
        self._commands.set_vcs(self._var_vcs.get() == 1)

    @action_decor
    def _on_set_squelch(self, _arg: str) -> None:
        assert self._commands
        sql = self._var_squelch.get()
        if sql == self._last_squelch:
            return

        self._var_label_squelch.set(consts.MONITOR_SQUELCH_LEVEL[sql])
        self._commands.set_squelch(sql)
        self._last_squelch = sql

    @action_decor
    def _on_set_volume(self, _arg: str) -> None:
        assert self._commands
        volume = self._var_volume.get()
        if volume == self._last_volume:
            return

        self._var_label_volume.set(str(volume))
        self._commands.set_volume(volume)
        self._last_volume = volume

    @action_decor
    def _on_change_tone(self) -> None:
        assert self._commands
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

    @action_decor
    def _change_freq(self, direction: int) -> None:
        assert self._commands

        step = consts.STEPS_KHZ[consts.STEPS.index(self._var_step.get())]
        if direction < 0:
            step *= -1

        freq = model.fmt.parse_freq(self._var_freq.get())
        freq = int(freq + step)
        freq = fixers.fix_frequency(freq)
        self._var_freq.set(model.fmt.format_freq(freq))

    def _set_frame_state(self, frame: tk.Widget, state: str) -> None:
        for widget in frame.children.values():
            if isinstance(widget, ttk.Combobox):
                widget["state"] = "readonly" if state == "normal" else state
            elif isinstance(
                widget,
                (
                    ttk.Entry,
                    ttk.Radiobutton,
                    ttk.Scale,
                    ttk.Checkbutton,
                    ttk.Button,
                ),
            ):
                widget["state"] = state
            elif isinstance(widget, (tk.Frame, ttk.LabelFrame)):
                self._set_frame_state(widget, state)

    def _set_frames_state(self, state: str) -> None:
        for frame in self._frames:
            self._set_frame_state(frame, state)


def validate_freq(freq: str) -> bool:
    if not freq:
        return False

    try:
        nfreq = model.fmt.parse_freq(freq)

    except Exception:
        _LOG.exception("freq: %r", freq)
        return False

    return consts.MIN_FREQUENCY <= nfreq <= consts.MAX_FREQUENCY

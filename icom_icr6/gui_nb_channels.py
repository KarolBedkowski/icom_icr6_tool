# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import tkinter as tk
from tkinter import messagebox, ttk

from . import gui_model, model
from .gui_widgets import build_list, new_checkbox, new_combo, new_entry


class ChannelsPage(tk.Frame):
    def __init__(
        self, parent: tk.Widget, radio_memory: model.RadioMemory
    ) -> None:
        super().__init__(parent)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._channel_model = gui_model.ChannelModel()
        self._radio_memory = radio_memory

        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self._channel_ranges = tk.Listbox(pw, selectmode=tk.SINGLE)
        self._channel_ranges.insert(tk.END, *gui_model.CHANNEL_RANGES)
        pw.add(self._channel_ranges, weight=0)
        self._channel_ranges.bind("<<ListboxSelect>>", self.__fill_channels)

        frame = tk.Frame(pw)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(1, weight=0)
        frame.columnconfigure(0, weight=1)

        self._create_channel_list(frame)
        self._create_fields(frame)

        pw.add(frame, weight=1)
        pw.grid(
            row=0, column=0, sticky=tk.N + tk.S + tk.E + tk.W, padx=6, pady=6
        )

    def set(self, radio_memory: model.RadioMemory) -> None:
        self._radio_memory = radio_memory
        self._channel_ranges.selection_set(0)
        self._channel_ranges.activate(0)

    def _create_channel_list(self, frame: tk.Frame) -> None:
        columns = (
            ("num", "Num", tk.E, 30),
            ("freq", "Freq", tk.E, 80),
            ("name", "Name", tk.W, 50),
            ("af", "AF", tk.CENTER, 25),
            ("att", "ATT", tk.CENTER, 25),
            ("mode", "Mode", tk.CENTER, 25),
            ("ts", "TS", tk.CENTER, 25),
            ("vsc", "VSC", tk.CENTER, 25),
            ("skip", "Skip", tk.CENTER, 25),
            ("bank", "Bank", tk.W, 25),
        )
        ccframe, self._channels_content = build_list(frame, columns)
        ccframe.grid(
            row=0, column=0, sticky=tk.N + tk.S + tk.E + tk.W, padx=6, pady=6
        )
        self._channels_content.bind(
            "<<TreeviewSelect>>", self.__on_channel_select
        )

    def _create_fields(self, frame: tk.Frame) -> None:
        fields = tk.Frame(frame)
        fields.columnconfigure(0, weight=0)
        fields.columnconfigure(1, weight=1)
        fields.columnconfigure(2, weight=0)
        fields.columnconfigure(3, weight=1)
        fields.columnconfigure(4, weight=0)
        fields.columnconfigure(5, weight=1)
        fields.columnconfigure(6, weight=0)
        fields.columnconfigure(7, weight=1)

        new_entry(fields, 0, 0, "Frequency: ", self._channel_model.freq)
        new_entry(fields, 0, 2, "Name: ", self._channel_model.name)
        new_combo(
            fields,
            0,
            4,
            "Mode: ",
            self._channel_model.mode,
            [" ", *model.MODES],
        )
        new_combo(
            fields,
            0,
            6,
            "TS: ",
            self._channel_model.ts,
            list(map(str, model.STEPS)),
        )
        # row 2
        new_combo(
            fields,
            1,
            0,
            "Duplex: ",
            self._channel_model.duplex,
            model.DUPLEX_DIRS,
        )
        new_entry(fields, 1, 2, "Offset: ", self._channel_model.offset)

        new_combo(
            fields, 1, 4, "Skip: ", self._channel_model.skip, model.SKIPS
        )
        new_checkbox(fields, 1, 6, " AF Filter", self._channel_model.af)
        new_checkbox(fields, 1, 7, " Attenuator", self._channel_model.attn)

        new_combo(
            fields, 2, 0, "Tone: ", self._channel_model.tmode, model.TONE_MODES
        )
        new_combo(
            fields,
            2,
            2,
            "TSQL: ",
            self._channel_model.ctone,
            list(model.CTCSS_TONES),
        )
        new_combo(
            fields, 2, 4, "DTSC: ", self._channel_model.dtsc, model.DTCS_CODES
        )
        new_combo(
            fields,
            2,
            6,
            "Polarity: ",
            self._channel_model.polarity,
            model.POLARITY,
        )

        new_checkbox(fields, 3, 0, " VSV", self._channel_model.vsc)
        new_combo(
            fields,
            3,
            2,
            "Bank: ",
            self._channel_model.bank,
            [" ", *model.BANK_NAMES],
        )
        new_entry(fields, 3, 4, "Bank pos: ", self._channel_model.bank_pos)

        ttk.Button(
            fields, text="Update", command=self.__on_channel_update
        ).grid(row=4, column=7, sticky=tk.E)
        ttk.Button(
            fields, text="Delete", command=self.__on_channel_delete
        ).grid(row=4, column=6, sticky=tk.E)

        fields.grid(row=1, column=0, sticky=tk.N + tk.S + tk.E + tk.W)

    def __on_channel_select(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._channels_content.selection()
        if not sel:
            return

        chan_num = int(sel[0])
        chan = self._radio_memory.get_channel(chan_num)
        self._channel_model.fill(chan)

    def __on_channel_update(self) -> None:
        sel = self._channels_content.selection()
        if not sel:
            return

        chan_num = int(sel[0])
        chan = self._radio_memory.get_channel(chan_num)
        self._channel_model.update_channel(chan)

        if errors := self._channel_model.validate():
            messagebox.showerror("Invalid configuration", "\n".join(errors))
            return

        if chan.freq:
            chan.hide_channel = False

        self.__fill_channels(None)
        self._channels_content.selection_set(sel)

    def __on_channel_delete(self) -> None:
        sel = self._channels_content.selection()
        if not sel:
            return

        if not messagebox.askyesno(
            "Delete channel",
            "Delete channel configuration?",
            icon=messagebox.WARNING,
        ):
            return

        chan_num = int(sel[0])
        chan = self._radio_memory.get_channel(chan_num)
        chan.delete()
        self.__fill_channels(None)
        self._channels_content.selection_set(sel)

    def __fill_channels(self, event: tk.Event | None) -> None:  # type: ignore
        selected_range = 0
        if sel := self._channel_ranges.curselection():  # type: ignore
            selected_range = sel[0]

        self._channels_content.delete(*self._channels_content.get_children())

        range_start = selected_range * 100
        for idx in range(range_start, range_start + 100):
            channel = self._radio_memory.get_channel(idx)
            if channel.hide_channel or not channel.freq:
                self._channels_content.insert(
                    parent="",
                    index=tk.END,
                    iid=idx,
                    text="",
                    values=(str(idx), "", "", "", "", "", "", "", "", ""),
                )
                continue

            try:
                bank = f"{model.BANK_NAMES[channel.bank]} {channel.bank_pos}"
            except IndexError:
                bank = ""

            self._channels_content.insert(
                parent="",
                index=tk.END,
                iid=idx,
                text="",
                values=(
                    str(idx),
                    str(channel.freq // 1000),
                    channel.name,
                    gui_model.yes_no(channel.af_filter),
                    gui_model.yes_no(channel.attenuator),
                    model.MODES[channel.mode],
                    model.STEPS[channel.tuning_step],
                    gui_model.yes_no(channel.vsc),
                    model.SKIPS[channel.skip],
                    bank,
                ),
            )
        if event is not None:
            self._channels_content.yview(0)
            self._channels_content.xview(0)

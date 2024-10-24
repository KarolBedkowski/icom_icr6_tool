# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
from tkinter import messagebox, ttk

from . import gui_model, model
from .gui_widgets import build_list, new_checkbox, new_combo, new_entry

_LOG = logging.getLogger(__name__)


class BanksPage(tk.Frame):
    def __init__(
        self, parent: tk.Widget, radio_memory: model.RadioMemory
    ) -> None:
        super().__init__(parent)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._bchan_model = gui_model.ChannelModel()
        self._bchan_number = tk.IntVar()
        self._bank_name = tk.StringVar()
        self._radio_memory = radio_memory

        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        banks = self._banks = tk.Listbox(pw, selectmode=tk.SINGLE)
        self.__fill_banks()

        banks.bind("<<ListboxSelect>>", self.__fill_bank)
        pw.add(banks, weight=0)

        frame = tk.Frame(pw)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(1, weight=0)
        frame.columnconfigure(0, weight=1)

        self._create_bank_fields(frame)
        self._create_bank_channels_list(frame)
        self._create_fields(frame)

        pw.add(frame, weight=1)

        pw.grid(
            row=0, column=0, sticky=tk.N + tk.S + tk.E + tk.W, padx=6, pady=6
        )

    def set(self, radio_memory: model.RadioMemory) -> None:
        self._radio_memory = radio_memory
        self._banks.selection_set(0)
        self._banks.activate(0)
        self.__fill_banks()

    def _create_bank_fields(self, frame: tk.Frame) -> None:
        fields = tk.Frame(frame)
        fields.columnconfigure(0, weight=0)
        fields.columnconfigure(1, weight=1)
        fields.columnconfigure(2, weight=0)
        new_entry(fields, 0, 0, "Bank name: ", self._bank_name)
        ttk.Button(fields, text="Update", command=self.__on_bank_update).grid(
            row=4, column=7, sticky=tk.E
        )

        fields.grid(row=0, column=0, sticky=tk.N + tk.S + tk.E + tk.W)

    def _create_bank_channels_list(self, frame: tk.Frame) -> None:
        columns = [
            ("num", "Num", tk.E, 30),
            ("chn", "Chn", tk.E, 30),
            ("freq", "freq", tk.E, 30),
            ("name", "name", tk.W, 30),
            ("ts", "ts", tk.CENTER, 30),
            ("mode", "mode", tk.CENTER, 30),
            ("af", "af", tk.CENTER, 30),
            ("att", "att", tk.CENTER, 30),
            ("vsc", "vsc", tk.CENTER, 30),
            ("skip", "skip", tk.CENTER, 30),
        ]
        ccframe, self._bank_content = build_list(frame, columns)
        ccframe.grid(
            row=0,
            column=0,
            sticky=tk.N + tk.S + tk.E + tk.W,
        )
        self._bank_content.bind("<<TreeviewSelect>>", self.__on_channel_select)

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

        new_entry(fields, 0, 0, "Channel: ", self._bchan_number)
        new_entry(fields, 1, 0, "Frequency: ", self._bchan_model.freq)
        new_entry(fields, 1, 2, "Name: ", self._bchan_model.name)
        new_combo(
            fields,
            1,
            4,
            "Mode: ",
            self._bchan_model.mode,
            [" ", *model.MODES],
        )
        new_combo(
            fields,
            1,
            6,
            "TS: ",
            self._bchan_model.ts,
            list(map(str, model.STEPS)),
        )
        new_combo(
            fields,
            2,
            0,
            "Duplex: ",
            self._bchan_model.duplex,
            model.DUPLEX_DIRS,
        )
        new_entry(fields, 2, 2, "Offset: ", self._bchan_model.offset)
        new_combo(fields, 2, 4, "Skip: ", self._bchan_model.skip, model.SKIPS)
        new_checkbox(fields, 2, 6, " AF Filter", self._bchan_model.af)
        new_checkbox(fields, 2, 7, " Attenuator", self._bchan_model.attn)

        new_combo(
            fields, 3, 0, "Tone: ", self._bchan_model.tmode, model.TONE_MODES
        )
        new_combo(
            fields,
            3,
            2,
            "TSQL: ",
            self._bchan_model.ctone,
            list(model.CTCSS_TONES),
        )
        new_combo(
            fields, 3, 4, "DTSC: ", self._bchan_model.dtsc, model.DTCS_CODES
        )
        new_combo(
            fields,
            3,
            6,
            "Polarity: ",
            self._bchan_model.polarity,
            model.POLARITY,
        )

        new_checkbox(fields, 4, 0, " VSV", self._bchan_model.vsc)

        ttk.Button(
            fields, text="Update", command=self.__on_channel_update
        ).grid(row=4, column=7, sticky=tk.E)
        ttk.Button(
            fields, text="Delete", command=self.__on_channel_delete
        ).grid(row=4, column=6, sticky=tk.E)

        fields.grid(row=1, column=0, sticky=tk.N + tk.S + tk.E + tk.W)

    def __fill_banks(self) -> None:
        banks = self._banks
        sel = banks.curselection()  # type: ignore
        banks.delete(0, banks.size())
        for idx, bname in enumerate(model.BANK_NAMES):
            bank = self._radio_memory.get_bank(idx)
            name = f"{bname}: {bank.name}" if bank.name else bname
            banks.insert(tk.END, name)

        if sel:
            banks.selection_set(sel[0])

    def __fill_bank(self, _event: tk.Event | None) -> None:  # type: ignore
        selected_bank = 0
        if sel := self._banks.curselection():  # type: ignore
            selected_bank = sel[0]

        bcont = self._bank_content
        bcont.delete(*bcont.get_children())

        bank = self._radio_memory.get_bank(selected_bank)
        self._bank_name.set(bank.name.rstrip())

        for idx, channel in enumerate(bank.channels):
            if not channel or channel.hide_channel or not channel.freq:
                bcont.insert(
                    parent="",
                    index=tk.END,
                    iid=idx,
                    text="",
                    values=(str(idx), "", "", "", "", "", "", "", "", ""),
                )
                continue

            bcont.insert(
                parent="",
                index=tk.END,
                iid=idx,
                text="",
                values=(
                    str(idx),
                    str(channel.number),
                    str(channel.freq // 1000),
                    channel.name,
                    model.STEPS[channel.tuning_step],
                    model.MODES[channel.mode],
                    gui_model.yes_no(channel.af_filter),
                    gui_model.yes_no(channel.attenuator),
                    gui_model.yes_no(channel.vsc),
                    model.SKIPS[channel.skip],
                ),
            )

        bcont.yview(0)
        bcont.xview(0)

    def __on_bank_update(self) -> None:
        if sel := self._banks.curselection():  # type: ignore
            selected_bank = sel[0]

        bank = self._radio_memory.get_bank(selected_bank)
        bank.name = self._bank_name.get().strip()[:6]
        self._radio_memory.set_bank(bank)
        self.__fill_banks()

    def __on_channel_select(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._bank_content.selection()
        if not sel:
            return

        selected_bank: int = int(self._banks.curselection()[0])  # type: ignore

        bank_chan_num = int(sel[0])
        bank = self._radio_memory.get_bank(selected_bank)
        if chan := bank.channels[bank_chan_num]:
            self._bchan_model.fill(chan)
            self._bchan_number.set(chan.number)
        else:
            self._bchan_model.reset()
            self._bchan_number.set("")  # type: ignore

    def __on_channel_update(self) -> None:
        pass

    def __on_channel_delete(self) -> None:
        sel = self._bank_content.selection()
        if not sel:
            return

        if not messagebox.askyesno(
            "Delete channel",
            "Delete channel configuration from bank?",
            icon=messagebox.WARNING,
        ):
            return

        selected_bank: int = int(self._banks.curselection()[0])  # type: ignore

        bank_chan_num = int(sel[0])
        bank = self._radio_memory.get_bank(selected_bank)
        if chan := bank.channels[bank_chan_num]:
            bank.channels[bank_chan_num] = None
            chan.clear_bank()

        self._bchan_model.reset()
        self._bchan_number.set("")  # type: ignore

        self.__fill_bank(None)
        self._bank_content.selection_set(sel)

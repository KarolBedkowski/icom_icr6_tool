# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import tkinter as tk
from tkinter import ttk

from . import gui_model, model
from .gui_widgets import build_list


class BanksPage(tk.Frame):
    def __init__(
        self, parent: tk.Widget, radio_memory: model.RadioMemory
    ) -> None:
        super().__init__(parent)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._radio_memory = radio_memory

        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        banks = self._banks = tk.Listbox(pw, selectmode=tk.SINGLE)
        self.__fill_banks()

        banks.bind("<<ListboxSelect>>", self.__fill_bank)
        pw.add(banks, weight=0)

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
        frame, self._bank_content = build_list(pw, columns)
        pw.add(frame, weight=1)

        pw.grid(
            row=0, column=0, sticky=tk.N + tk.S + tk.E + tk.W, padx=6, pady=6
        )

    def set(self, radio_memory: model.RadioMemory) -> None:
        self._radio_memory = radio_memory
        self._banks.selection_set(0)
        self._banks.activate(0)
        self.__fill_banks()

    def __fill_banks(self) -> None:
        banks = self._banks
        banks.delete(0, banks.size())
        for idx, bname in enumerate(model.BANK_NAMES):
            bank = self._radio_memory.get_bank(idx)
            name = f"{bname}: {bank.name}" if bank.name else bname
            banks.insert(tk.END, name)

    def __fill_bank(self, _event: tk.Event) -> None:  # type: ignore
        selected_bank = 0
        if sel := self._banks.curselection():  # type: ignore
            selected_bank = sel[0]

        bcont = self._bank_content
        bcont.delete(*bcont.get_children())

        bank = self._radio_memory.get_bank(selected_bank)

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

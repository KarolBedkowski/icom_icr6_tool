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
from .gui_widgets import (
    NumEntryPopup,
    TableView2,
    TableViewModelRow,
    UpdateCellResult,
    build_list_model,
    new_entry,
)

_LOG = logging.getLogger(__name__)


class BanksPage(tk.Frame):
    def __init__(
        self, parent: tk.Widget, radio_memory: model.RadioMemory
    ) -> None:
        super().__init__(parent)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._bchan_number = tk.IntVar()
        self._bank_number = tk.IntVar()
        self._bank_name = tk.StringVar()
        self._radio_memory = radio_memory

        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        banks = self._banks = tk.Listbox(pw, selectmode=tk.SINGLE)
        self.__fill_banks()

        banks.bind("<<ListboxSelect>>", self.__fill_bank)
        pw.add(banks, weight=0)

        frame = tk.Frame(pw)
        frame.rowconfigure(0, weight=0)
        frame.rowconfigure(1, weight=1)
        frame.rowconfigure(2, weight=0)
        frame.columnconfigure(0, weight=1)

        self._create_bank_fields(frame)
        self._create_bank_channels_list(frame)

        pw.add(frame, weight=1)

        pw.grid(
            row=0, column=0, sticky=tk.N + tk.S + tk.E + tk.W, padx=6, pady=6
        )

    def set(self, radio_memory: model.RadioMemory) -> None:
        self._radio_memory = radio_memory
        self.__fill_banks()

    def _create_bank_fields(self, frame: tk.Frame) -> None:
        fields = tk.Frame(frame)
        fields.columnconfigure(0, weight=0)
        fields.columnconfigure(1, weight=1)
        fields.columnconfigure(2, weight=0)
        validator = self.register(validate_bank_name)
        new_entry(
            fields, 0, 0, "Bank name: ", self._bank_name, validator=validator
        )
        ttk.Button(fields, text="Update", command=self.__on_bank_update).grid(
            row=0, column=7, sticky=tk.E
        )

        fields.grid(row=0, column=0, sticky=tk.N + tk.E + tk.W + tk.S, ipady=6)

    def _create_bank_channels_list(self, frame: tk.Frame) -> None:
        self._tb_model = BankChannelsListModel(
            self._radio_memory, self._bank_number
        )
        ccframe, self._bank_content = build_list_model(frame, self._tb_model)
        ccframe.grid(
            row=1, column=0, sticky=tk.N + tk.S + tk.E + tk.W, ipady=6
        )
        self._bank_content.bind(
            "<<TreeviewSelect>>", self.__on_channel_select, add="+"
        )

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

    def __fill_bank(self, event: tk.Event | None) -> None:  # type: ignore
        if sel := self._banks.curselection():  # type: ignore
            selected_bank = sel[0]
        else:
            return

        bcont = self._bank_content

        bank = self._radio_memory.get_bank(selected_bank)
        self._bank_name.set(bank.name.rstrip())
        self._bank_number.set(selected_bank)

        self._tb_model.data = [
            self._radio_memory.get_channel(channum)
            if channum is not None
            else None
            for idx, channum in enumerate(bank.channels)
        ]
        bcont.update_all()

        if event:
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
            self._bchan_number.set(chan)
        else:
            self._bchan_number.set("")  # type: ignore

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

        self._bchan_number.set("")  # type: ignore

        self.__fill_bank(None)
        self._bank_content.selection_set(bank_chan_num)


class BankChannelsListModel(gui_model.ChannelsListModel):
    def __init__(
        self, radio_memory: model.RadioMemory, banknum: tk.IntVar
    ) -> None:
        super().__init__(radio_memory)
        self._bank_number = banknum

    def _columns(self) -> ty.Iterable[gui_model.TableViewColumn]:
        tvc = gui_model.TableViewColumn
        return (
            tvc("num", "Num", tk.E, 30),
            tvc("chan", "Chan", tk.E, 30),
            tvc("freq", "Freq", tk.E, 80),
            tvc("mode", "Mode", tk.CENTER, 25),
            tvc("name", "Name", tk.W, 50),
            tvc("af", "AF", tk.CENTER, 25),
            tvc("att", "ATT", tk.CENTER, 25),
            tvc("ts", "TS", tk.CENTER, 40),
            tvc("duplex", "DUP", tk.CENTER, 25),
            tvc("offset", "Offset", tk.E, 60),
            tvc("skip", "Skip", tk.CENTER, 25),
            tvc("vsc", "VSC", tk.CENTER, 25),
            tvc("tone", "Tone", tk.CENTER, 30),
            tvc("tsql", "TSQL", tk.E, 40),
            tvc("dtsc", "DTSC", tk.E, 30),
            tvc("polarity", "Polarity", tk.CENTER, 35),
        )

    def _data2iid(self, chan: model.Channel) -> str:
        return str(chan.bank_pos)

    def data2row(self, channel: model.Channel | None) -> TableViewModelRow:
        if channel is None:
            return ()

        return (
            str(channel.bank_pos),
            str(channel.number),
            str(channel.freq // 1000),
            model.MODES[channel.mode],
            channel.name.rstrip(),
            gui_model.yes_no(channel.af_filter),
            gui_model.yes_no(channel.attenuator),
            model.STEPS[channel.tuning_step],
            model.DUPLEX_DIRS[channel.duplex],
            str(channel.offset // 1000) if channel.duplex else "",
            model.SKIPS[channel.skip],
            gui_model.yes_no(channel.vsc),
            model.TONE_MODES[channel.tmode],
            gui_model.get_or_default(model.CTCSS_TONES, channel.ctone)
            if channel.tmode in (1, 2)
            else "",
            gui_model.get_or_default(model.DTCS_CODES, channel.dtsc)
            if channel.tmode in (3, 4)
            else "",
            model.POLARITY[channel.polarity]
            if channel.tmode in (3, 4)
            else "",
        )

    def get_editor(
        self,
        row: int,
        column: int,
        value: str,
        parent: TableView2[model.Channel],
    ) -> tk.Widget | None:
        coldef = self.columns[column]

        if coldef.colid != "chan":
            return super().get_editor(row, column, value, parent)

        return NumEntryPopup(
            parent,
            str(row),
            column,
            value,
            max_val=model.NUM_CHANNELS,
        )

    def update_cell(
        self,
        row: int,  # row
        column: int,
        value: str | None,  # new value
    ) -> tuple[UpdateCellResult, model.Channel | None]:
        coldef = self.columns[column]
        if coldef.colid != "chan":
            return super().update_cell(row, column, value)

        bank_num = self._bank_number.get()
        bank = self._radio_memory.get_bank(bank_num)

        if not value:
            if channum := bank.channels[row]:
                chan = self._radio_memory.get_channel(channum)
                chan.clear_bank()
                self._radio_memory.set_channel(chan)

                return UpdateCellResult.UPDATE_ROW, chan

            return UpdateCellResult.NOOP, None

        channum = int(value)
        assert 0 <= channum < model.NUM_CHANNELS
        chan = self._radio_memory.get_channel(channum)

        res = (
            UpdateCellResult.UPDATE_ALL
            if channum in bank.channels
            else UpdateCellResult.UPDATE_ROW
        )

        chan.bank = bank_num
        chan.bank_pos = row

        self._radio_memory.set_channel(chan)
        self.data[row] = chan

        return res, chan


def validate_bank_name(name: str | None) -> bool:
    if not name:
        return True

    try:
        model.validate_name(name)
    except ValueError:
        return False

    return True

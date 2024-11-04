# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from tkinter import messagebox, ttk

from . import consts, expimp, gui_model, model
from .gui_widgets import (
    NumEntryPopup,
    TableView2,
    TableViewColumn,
    TableViewModelRow,
    UpdateCellResult,
    build_list_model,
    new_checkbox,
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

        self._bank_name = tk.StringVar()
        self._bank_link = gui_model.BoolVar()
        self._radio_memory = radio_memory

        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        banks = self._banks_list = tk.Listbox(pw, selectmode=tk.SINGLE)

        banks.bind("<<ListboxSelect>>", self.__update_chan_list)
        pw.add(banks, weight=0)

        frame = tk.Frame(pw)
        self.__create_bank_fields(frame)
        self.__create_chan_list(frame)
        pw.add(frame, weight=1)

        pw.pack(expand=True, fill=tk.BOTH, side=tk.TOP, padx=12, pady=12)

        self.__update_banks_list()

    def set(self, radio_memory: model.RadioMemory) -> None:
        self._radio_memory = radio_memory
        self.__update_banks_list()

    def __create_bank_fields(self, frame: tk.Frame) -> None:
        fields = tk.Frame(frame)
        fields.columnconfigure(0, weight=0)
        fields.columnconfigure(1, weight=0)
        fields.columnconfigure(2, weight=0)
        fields.columnconfigure(3, weight=0)

        validator = self.register(validate_bank_name)
        self._field_bank_name = new_entry(
            fields, 0, 0, "Bank name: ", self._bank_name, validator=validator
        )
        self._field_bank_link = new_checkbox(
            fields, 0, 2, "Bank link", self._bank_link
        )
        self._btn_update = ttk.Button(
            fields, text="Update", command=self.__on_bank_update
        )
        self._btn_update.grid(row=0, column=3, sticky=tk.E, padx=6)

        fields.pack(side=tk.TOP, fill=tk.X, ipady=6)

    def __create_chan_list(self, frame: tk.Frame) -> None:
        self._chan_list_model = BankChannelsListModel(self._radio_memory)
        ccframe, self._bank_content = build_list_model(
            frame, self._chan_list_model
        )
        ccframe.pack(side=tk.TOP, expand=True, fill=tk.BOTH, ipady=6)

        self._bank_content.bind(
            "<<TreeviewSelect>>", self.__on_channel_select, add="+"
        )
        self._bank_content.bind("<Delete>", self.__on_channel_delete)
        self._bank_content.bind("<Control-c>", self.__on_channel_copy)
        self._bank_content.bind("<Control-v>", self.__on_channel_paste)

    def __update_banks_list(self) -> None:
        banks = self._banks_list
        sel = banks.curselection()  # type: ignore

        banks.delete(0, banks.size())
        for idx, bname in enumerate(consts.BANK_NAMES):
            bank = self._radio_memory.get_bank(idx)
            name = f"{bname}: {bank.name}" if bank.name else bname
            banks.insert(tk.END, name)

        if sel:
            banks.selection_set(sel[0])
        else:
            self._field_bank_name["state"] = "disabled"
            self._field_bank_link["state"] = "disabled"
            self._btn_update["state"] = "disabled"
            self._chan_list_model.clear()
            self._bank_content.update_all()
            self._bank_name.set("")

    def __update_chan_list(self, event: tk.Event | None) -> None:  # type: ignore
        bcont = self._bank_content

        if sel := self._banks_list.curselection():  # type: ignore
            selected_bank = sel[0]
        else:
            self._chan_list_model.data.clear()
            bcont.update_all()
            return

        bank = self._radio_memory.get_bank(selected_bank)
        self._bank_name.set(bank.name.rstrip())

        bl = self._radio_memory.get_bank_links()
        self._bank_link.set_raw(bl[selected_bank])

        self._chan_list_model.set_bank(selected_bank, bank)
        bcont.update_all()

        if event:
            bcont.yview(0)
            bcont.xview(0)

        self._field_bank_name["state"] = "normal"
        self._field_bank_link["state"] = "normal"
        self._btn_update["state"] = "normal"

    def _get_selections(self) -> tuple[int | None, int | None]:
        """selected bank, selected bank pos."""
        sel_bank = self._banks_list.curselection()  # type: ignore
        sel_pos = self._bank_content.selection()

        return (
            (sel_bank[0] if sel_bank else None),
            (int(sel_pos[0]) if sel_pos else None),
        )

    def _get_selected_channel(self) -> model.Channel | None:
        sel = self._bank_content.selection()
        if not sel:
            return None

        bank_pos = int(sel[0])
        selected_bank: int = int(self._banks_list.curselection()[0])  # type: ignore
        bank = self._radio_memory.get_bank(selected_bank)
        if channum := bank.channels[bank_pos]:
            chan = self._radio_memory.get_channel(channum)
            _LOG.debug("selected: %r", chan)
            return chan

        return None

    def __on_bank_update(self) -> None:
        if sel := self._banks_list.curselection():  # type: ignore
            selected_bank = sel[0]
        else:
            return

        bank = self._radio_memory.get_bank(selected_bank)
        bank.name = self._bank_name.get().strip()[:6]
        self._radio_memory.set_bank(bank)

        bl = self._radio_memory.get_bank_links()
        bl[selected_bank] = self._bank_link.get_raw()
        self._radio_memory.set_bank_links(bl)

        self.__update_banks_list()

    def __on_channel_select(self, _event: tk.Event) -> None:  # type: ignore
        self._get_selected_channel()

    def __on_channel_delete(self, _event: tk.Event) -> None:  # type: ignore
        chan = self._get_selected_channel()
        if not chan:
            return

        if not messagebox.askyesno(
            "Delete channel",
            "Delete channel configuration from bank?",
            icon=messagebox.WARNING,
        ):
            return

        sel = self._bank_content.selection()
        chan.clear_bank()
        self._radio_memory.set_channel(chan)

        self.__update_chan_list(None)
        self._bank_content.selection_set(sel[0])

    def __on_channel_copy(self, _event: tk.Event) -> None:  # type: ignore
        if chan := self._get_selected_channel():
            clip = gui_model.Clipboard.get()
            clip.put("channel", expimp.export_channel_str(chan))

    def __on_channel_paste(self, _event: tk.Event) -> None:  # type: ignore
        selected_bank, bank_pos = self._get_selections()
        if selected_bank is None or bank_pos is None:
            return

        clip = gui_model.Clipboard.get()
        if clip.object_type != "channel":
            return

        chan = self._get_selected_channel()
        if chan:
            # replace
            _LOG.debug("replacing channel: %r", chan)
        else:
            # insert, find first hidden channel
            # TODO: insert, find next after pasted?
            chan = self._radio_memory.find_first_hidden_channel()
            if not chan:
                _LOG.warn("no hidden channel found")
                return

        try:
            expimp.import_channel_str(chan, ty.cast(str, clip.content))
        except Exception:
            _LOG.exception("import from clipboard error")
            return

        chan.bank = selected_bank
        chan.bank_pos = bank_pos
        chan.hide_channel = False

        self._radio_memory.set_channel(chan)
        self.__update_chan_list(None)


class BankChannelsListModel(gui_model.ChannelsListModel):
    def __init__(self, radio_memory: model.RadioMemory) -> None:
        super().__init__(radio_memory)
        self._bank_number = -1

    def _columns(self) -> ty.Iterable[TableViewColumn]:
        tvc = TableViewColumn
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

        if not channel.freq or channel.hide_channel:
            return (
                str(channel.bank_pos),
                str(channel.number),
                "!",
            )

        return (
            str(channel.bank_pos),
            str(channel.number),
            gui_model.format_freq(channel.freq // 1000),
            consts.MODES[channel.mode],
            channel.name.rstrip(),
            gui_model.yes_no(channel.af_filter),
            gui_model.yes_no(channel.attenuator),
            consts.STEPS[channel.tuning_step],
            consts.DUPLEX_DIRS[channel.duplex],
            gui_model.format_freq(channel.offset // 1000)
            if channel.duplex
            else "",
            consts.SKIPS[channel.skip],
            gui_model.yes_no(channel.vsc),
            consts.TONE_MODES[channel.tone_mode],
            gui_model.get_or_default(consts.CTCSS_TONES, channel.tsql_freq)
            if channel.tone_mode in (1, 2)
            else "",
            gui_model.get_or_default(consts.DTCS_CODES, channel.dtsc)
            if channel.tone_mode in (3, 4)
            else "",
            consts.POLARITY[channel.polarity]
            if channel.tone_mode in (3, 4)
            else "",
        )

    def get_editor(
        self,
        row: int,
        column: int,
        value: str,
        parent: TableView2[model.Channel | None],
    ) -> tk.Widget | None:
        coldef = self.columns[column]

        if coldef.colid != "chan":
            return super().get_editor(row, column, value, parent)

        return NumEntryPopup(
            parent,
            str(row),
            column,
            value,
            max_val=consts.NUM_CHANNELS,
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

        _LOG.debug("update_cell: %r,%r = %r", row, column, value)

        bank_num = self.bank_num
        bank = self._radio_memory.get_bank(bank_num)

        if not value:
            # remove channel from bank
            if channum := bank.channels[row]:
                chan = self._radio_memory.get_channel(channum)
                _LOG.debug("clean bank in: %r", chan)
                chan.clear_bank()
                self._radio_memory.set_channel(chan)
                self.data[row] = None

                return UpdateCellResult.UPDATE_ROW, None

            _LOG.error("not found channel %d in bank %r", row, bank)
            return UpdateCellResult.NOOP, None

        channum = int(value)
        assert 0 <= channum < consts.NUM_CHANNELS
        # new channel to set
        chan = self._radio_memory.get_channel(channum)

        # check if replacing other channel in this bank
        try:
            idx = bank.channels.index(channum)
        except ValueError:
            res = UpdateCellResult.UPDATE_ROW
        else:
            self.data[idx] = None
            res = UpdateCellResult.UPDATE_ALL

        chan.bank = bank_num
        chan.bank_pos = row

        self._radio_memory.set_channel(chan)
        self.data[row] = chan

        return res, chan

    def clear(self) -> None:
        self.bank_num = -1
        self.data.clear()

    def set_bank(self, bank_num: int, bank: model.Bank) -> None:
        self.data = [
            self._radio_memory.get_channel(channum)
            if channum is not None
            else None
            for channum in bank.channels
        ]
        self.bank_num = bank_num


def validate_bank_name(name: str | None) -> bool:
    if not name:
        return True

    try:
        model.validate_name(name)
    except ValueError:
        return False

    return True

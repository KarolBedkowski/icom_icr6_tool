# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
from tkinter import messagebox, ttk

from . import gui_model, model
from .gui_widgets import (
    CheckboxPopup,
    ComboboxPopup,
    EntryPopup,
    NumEntryPopup,
    TableView2,
    TableViewColumn,
    TableViewModel,
    TableViewModelRow,
    build_list_model,
)

_LOG = logging.getLogger(__name__)


class ChannelsPage(tk.Frame):
    def __init__(
        self, parent: tk.Widget, radio_memory: model.RadioMemory
    ) -> None:
        super().__init__(parent)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._radio_memory = radio_memory

        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self._channel_ranges = tk.Listbox(pw, selectmode=tk.SINGLE)
        self._channel_ranges.insert(tk.END, *gui_model.CHANNEL_RANGES)
        self._channel_ranges.bind("<<ListboxSelect>>", self.__fill_channels)
        pw.add(self._channel_ranges, weight=0)

        frame = tk.Frame(pw)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(1, weight=0)
        frame.columnconfigure(0, weight=1)

        self._create_channel_list(frame)

        pw.add(frame, weight=1)
        pw.grid(
            row=0, column=0, sticky=tk.N + tk.S + tk.E + tk.W, padx=6, pady=6
        )

    def set(self, radio_memory: model.RadioMemory) -> None:
        self._radio_memory = radio_memory
        self._channel_ranges.activate(0)
        self._channel_ranges.selection_set(0)

    def _create_channel_list(self, frame: tk.Frame) -> None:
        self._tb_model = ChannelsListModel(self._radio_memory)
        ccframe, self._channels_content = build_list_model(
            frame, self._tb_model
        )
        ccframe.grid(
            row=0,
            column=0,
            sticky=tk.N + tk.S + tk.E + tk.W,
        )
        self._channels_content.bind(
            "<<TreeviewSelect>>", self.__on_channel_select, add="+"
        )

    def __on_channel_select(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._channels_content.selection()
        if not sel:
            return

        chan_num = int(sel[0])
        chan = self._radio_memory.get_channel(chan_num)
        _LOG.debug("chan: %r", chan)

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
        self._radio_memory.set_channel(chan)
        self.__fill_channels(None)
        self._channels_content.selection_set(sel)

    def __fill_channels(self, event: tk.Event | None) -> None:  # type: ignore
        if sel := self._channel_ranges.curselection():  # type: ignore
            selected_range = sel[0]
        else:
            return

        self._channels_content.delete(*self._channels_content.get_children())

        range_start = selected_range * 100
        self._tb_model.data = [
            self._radio_memory.get_channel(idx)
            for idx in range(range_start, range_start + 100)
        ]
        self._channels_content.update_all()

        if event is not None:
            self._channels_content.yview(0)
            self._channels_content.xview(0)


class ChannelsListModel(TableViewModel[model.Channel]):
    def __init__(self, radio_memory: model.RadioMemory) -> None:
        tvc = TableViewColumn
        super().__init__(
            (
                tvc("num", "Num", tk.E, 30),
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
                tvc("bank", "Bank", tk.CENTER, 25),
                tvc("bank_pos", "Bank pos", tk.W, 25),
            )
        )
        self._radio_memory = radio_memory

    def get_editor(
        self,
        row: int,
        column: int,
        value: str,
        parent: TableView2[model.Channel],
    ) -> tk.Widget | None:
        coldef = self.columns[column]
        iid = str(self.data[row].number)
        chan = self.data[row]
        _LOG.debug(
            "get_editor: row=%d[%r], col=%d[%s], value=%r, chan=%r",
            row,
            iid,
            column,
            coldef.colid,
            value,
            chan,
        )
        match coldef.colid:
            case "num":  # num
                return None

            case "af" | "att" | "vsc":
                return CheckboxPopup(parent, iid, column, value)

            case "mode":
                return ComboboxPopup(parent, iid, column, value, model.MODES)

            case "ts":
                return ComboboxPopup(parent, iid, column, value, model.STEPS)

            case "duplex":
                return ComboboxPopup(
                    parent, iid, column, value, model.DUPLEX_DIRS
                )

            case "skip":
                return ComboboxPopup(parent, iid, column, value, model.SKIPS)

            case "tone":
                return ComboboxPopup(
                    parent, iid, column, value, model.TONE_MODES
                )

            case "tsql":
                if chan.tmode not in (1, 2):
                    return None

                return ComboboxPopup(
                    parent, iid, column, value, model.CTCSS_TONES
                )

            case "dtsc":
                if chan.tmode not in (3, 4):
                    return None

                return ComboboxPopup(
                    parent, iid, column, value, model.DTCS_CODES
                )

            case "polarity":
                if chan.tmode not in (3, 4):
                    return None

                return ComboboxPopup(
                    parent, iid, column, value, model.POLARITY
                )
            case "offset":
                if not chan.duplex:
                    return None

                return NumEntryPopup(
                    parent, iid, column, value, min_val=0, max_val=159995
                )

            case "name":
                return EntryPopup(parent, iid, column, value).with_validator(
                    gui_model.name_validator
                )

            case "bank":
                return ComboboxPopup(
                    parent, iid, column, value, list(model.BANK_NAMES)
                )

            case "bank_pos":
                if chan.bank == model.BANK_NOT_SET:
                    return None

                return NumEntryPopup(parent, iid, column, value, max_val=99)

            case "freq":
                return NumEntryPopup(
                    parent,
                    iid,
                    column,
                    value,
                    max_val=model.MAX_FREQUENCY // 1000,
                )

        return None

    def update_cell(
        self,
        row: int,  # row
        column: int,
        value: str | None,  # new value
    ) -> model.Channel | None:
        chan = self.data[row]
        _LOG.debug("update chan: %r", chan)

        coldef = self.columns[column]
        if (not chan.freq or chan.hide_channel) and coldef.colid != "freq":
            return None

        match coldef.colid:
            case "num":  # num
                return None

            case "freq":
                chan.freq = (
                    model.fix_frequency(int(value) * 1000) if value else 0
                )
                if chan.freq and chan.hide_channel:
                    chan.hide_channel = False
                    chan.mode = model.default_mode_for_freq(chan.freq)

            case "mode":
                chan.mode = model.MODES.index(value) if value else 0

            case "name":
                chan.name = model.fix_name(value or "")

            case "af":
                chan.af_filter = value == "yes"

            case "att":
                chan.attenuator = value == "yes"

            case "ts":
                chan.tuning_step = model.STEPS.index(value) if value else 0

            case "duplex":
                chan.duplex = model.DUPLEX_DIRS.index(value) if value else 0

            case "offset":
                chan.offset = int(value or 0) * 1000

            case "skip":
                chan.skip = model.SKIPS.index(value) if value else 0

            case "tone":
                chan.tmode = gui_model.get_index_or_default(
                    model.TONE_MODES, value, 0
                )

            case "tsql":
                chan.ctone = gui_model.get_index_or_default(
                    model.CTCSS_TONES, value, 63
                )

            case "dtsc":
                chan.dtsc = gui_model.get_index_or_default(
                    model.DTCS_CODES, value, 127
                )

            case "polarity":
                chan.polarity = gui_model.get_index_or_default(
                    model.POLARITY, value, 0
                )

            case "vsc":
                chan.vsc = value == "yes"

            case "bank":
                prev_bank = chan.bank
                chan.bank = gui_model.get_index_or_default(
                    list(model.BANK_NAMES), value, model.BANK_NOT_SET
                )
                if chan.bank not in (prev_bank, model.BANK_NOT_SET):
                    bank = self._radio_memory.get_bank(chan.bank)
                    pos = bank.find_free_slot()
                    chan.bank_pos = pos if pos is not None else 99

            case "bank_pos":
                bank_pos = 0
                if chan.bank != model.BANK_NOT_SET:
                    bank_pos = int(value or 0)
                    bank = self._radio_memory.get_bank(chan.bank)
                    if bank.channels[bank_pos] != chan.number:
                        # selected slot is used by another channel

                        # find unused next slot
                        pos = bank.find_free_slot(bank_pos)
                        if pos is None:
                            # find first unused slot
                            pos = bank.find_free_slot()

                        if pos is not None:
                            bank_pos = pos
                        # else: not found unused slot - replace

                chan.bank_pos = bank_pos

        _LOG.debug("new chan: %r", chan)
        self._radio_memory.set_channel(chan)
        return chan

    def data2row(self, channel: model.Channel) -> TableViewModelRow:
        if channel.hide_channel or not channel.freq:
            return (str(channel.number),)

        try:
            bank = model.BANK_NAMES[channel.bank]
            bank_pos = str(channel.bank_pos)
        except IndexError:
            bank = bank_pos = ""

        return (
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
            bank,
            bank_pos,
        )

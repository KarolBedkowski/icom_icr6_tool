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
    TableView2,
    TableViewColumn,
    TableViewModel,
    TableViewModelRow,
    build_list_model,
    new_checkbox,
    new_combo,
    new_entry,
)

_LOG = logging.getLogger(__name__)


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
        self._channel_ranges.bind("<<ListboxSelect>>", self.__fill_channels)
        pw.add(self._channel_ranges, weight=0)

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
        _LOG.debug("chan: %r", chan)
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

        _LOG.debug("chan: %r", chan)

        self._radio_memory.set_channel(chan)

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
        TVC = TableViewColumn
        super().__init__(
            (
                TVC("num", "Num", tk.E, 30),
                TVC("freq", "Freq", tk.E, 80),
                TVC("name", "Name", tk.W, 50),
                TVC("af", "AF", tk.CENTER, 25),
                TVC("att", "ATT", tk.CENTER, 25),
                TVC("mode", "Mode", tk.CENTER, 25),
                TVC("ts", "TS", tk.CENTER, 25),
                TVC("vsc", "VSC", tk.CENTER, 25),
                TVC("skip", "Skip", tk.CENTER, 25),
                TVC("bank", "Bank", tk.W, 25),
            )
        )
        self._radio_memory = radio_memory

    def get_editor(
        self,
        row: int,
        column: int,
        value: str,
        parent: TableView2,
    ) -> tk.Widget | None:
        coldef = self.columns[column]
        iid = str(self.data[row].number)
        match coldef.colid:
            case "num":  # num
                return None

            case "af" | "att" | "vsc":
                return CheckboxPopup(parent, iid, column, value)

            case "mode":
                return ComboboxPopup(parent, iid, column, value, model.MODES)

            case "ts":
                return ComboboxPopup(parent, iid, column, value, model.STEPS)

        return EntryPopup(parent, iid, column, value)

    def update_cell(
        self,
        row: int,  # row
        column: int,
        value: str | None,  # new value
    ) -> model.Channel | None:
        chan = self.data[row]
        _LOG.debug("update chan: %r", chan)

        coldef = self.columns[column]
        match coldef.colid:
            case "num":  # num
                return None

            case "name":
                chan.name = value.rstrip()[:6].upper() if value else ""

            case "freq":
                chan.freq = int(value) * 1000 if value else 0
                if chan.freq and chan.hide_channel:
                    chan.hide_channel = False
                    if chan.freq > 110:  # TODO: check
                        chan.mode = 0
                    if chan.freq > 68:
                        chan.mode = 1
                    if chan.freq > 30:
                        chan.mode = 0
                    else:
                        chan.mode = 2

            case "af":
                chan.af_filter = value == "yes"

            case "att":
                chan.attenuator = value == "yes"

            case "vsc":
                chan.vsc = value == "yes"

            case "mode":
                chan.mode = model.MODES.index(value) if value else 0

            case "ts":
                chan.tuning_step = model.STEPS.index(value) if value else 0

            case "skip":
                chan.skip = model.SKIPS.index(value) if value else 0

            # case "duplex":
            #     chan.duplex = model.DUPLEX_DIRS.index(value) if value else 0

            # case "offset":
            #     chan.offset = int(value or 0) * 1000

            # case "tmchan.tmode = model.TONE_MODES.index(self.tmode.get())
        # chan.ctone = _get_index_or_default(
        # model.CTCSS_TONES, self.ctone.get(), 63
        # )
        # chan.dtsc = _get_index_or_default(
        # model.DTCS_CODES, self.dtsc.get(), 127
        # )
        # chan.polarity = _get_index_or_default(
        # model.POLARITY, self.polarity.get(), 0
        # )

        _LOG.debug("new chan: %r", chan)
        self._radio_memory.set_channel(chan)
        return chan

    def data2row(self, channel: model.Channel) -> TableViewModelRow:
        if channel.hide_channel or not channel.freq:
            return (str(channel.number), "", "", "", "", "", "", "", "", "")

        try:
            bank = f"{model.BANK_NAMES[channel.bank]} {channel.bank_pos}"
        except IndexError:
            bank = ""

        return (
            str(channel.number),
            str(channel.freq // 1000),
            channel.name,
            gui_model.yes_no(channel.af_filter),
            gui_model.yes_no(channel.attenuator),
            model.MODES[channel.mode],
            model.STEPS[channel.tuning_step],
            gui_model.yes_no(channel.vsc),
            model.SKIPS[channel.skip],
            bank,
        )

# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from tkinter import messagebox, ttk

from . import consts, expimp, gui_model, model
from .gui_widgets import build_list_model

_LOG = logging.getLogger(__name__)


class ChannelsPage(tk.Frame):
    def __init__(
        self, parent: tk.Widget, radio_memory: model.RadioMemory
    ) -> None:
        super().__init__(parent)
        self._parent = parent
        self._radio_memory = radio_memory
        self._last_selected_groupg = 0

        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self._groups_list = tk.Listbox(pw, selectmode=tk.SINGLE)
        self._groups_list.insert(tk.END, *gui_model.CHANNEL_RANGES)
        self._groups_list.bind("<<ListboxSelect>>", self.__update_chan_list)
        pw.add(self._groups_list, weight=0)

        frame = tk.Frame(pw)
        self._create_channel_list(frame)
        pw.add(frame, weight=1)

        pw.pack(expand=True, fill=tk.BOTH, side=tk.TOP, padx=12, pady=12)

    def set(
        self, radio_memory: model.RadioMemory, *, activate: bool = False
    ) -> None:
        self._radio_memory = radio_memory

        # hide canceller in global models
        cols = self._channels_list["columns"]
        if not radio_memory.is_usa_model():
            cols = [c for c in cols if c not in ("canc", "canc_freq")]

        self._channels_list["displaycolumns"] = cols

        if activate:
            self._groups_list.selection_set(self._last_selected_groupg)

        self.__update_chan_list()

    def _create_channel_list(self, frame: tk.Frame) -> None:
        self._tb_model = gui_model.ChannelsListModel(self._radio_memory)
        ccframe, self._channels_list = build_list_model(frame, self._tb_model)
        ccframe.pack(side=tk.TOP, expand=True, fill=tk.BOTH, ipady=6)

        self._channels_list.bind(
            "<<TreeviewSelect>>", self.__on_channel_select, add="+"
        )
        self._channels_list.bind("<Delete>", self.__on_channel_delete)
        self._channels_list.bind("<Control-c>", self.__on_channel_copy)
        self._channels_list.bind("<Control-v>", self.__on_channel_paste)

    def __on_channel_select(self, _event: tk.Event) -> None:  # type: ignore
        for sel in self._channels_list.selection():
            chan_num = int(sel)
            chan = self._radio_memory.get_channel(chan_num)
            _LOG.debug("chan: %r", chan)

    def __on_channel_delete(self, _event: tk.Event) -> None:  # type: ignore
        with self._channels_list.with_sellection() as sel:
            if not sel:
                return

            if not messagebox.askyesno(
                "Delete channel",
                "Delete channel configuration?",
                icon=messagebox.WARNING,
            ):
                return

            for chan_num in sel:
                chan = self._radio_memory.get_channel(int(chan_num))
                chan.delete()
                self._radio_memory.set_channel(chan)

            self.__update_chan_list()

    def __update_chan_list(self, event: tk.Event | None = None) -> None:  # type: ignore
        if sel := self._groups_list.curselection():  # type: ignore
            selected_range = sel[0]
        else:
            self._tb_model.data.clear()
            self._channels_list.update_all()
            return

        self._last_selected_groupg = sel[0]

        range_start = selected_range * 100
        self._tb_model.data = [
            self._radio_memory.get_channel(idx)
            for idx in range(range_start, range_start + 100)
        ]
        self._channels_list.update_all()

        self._show_stats()

        if event is not None:
            self._channels_list.yview(0)
            self._channels_list.xview(0)

    def __on_channel_copy(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._channels_list.selection()
        if not sel:
            return

        channels = (
            self._radio_memory.get_channel(int(chan_num)) for chan_num in sel
        )
        clip = gui_model.Clipboard.instance()
        clip.put(expimp.export_channel_str(channels))

    def __on_channel_paste(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._channels_list.selection()
        if not sel:
            return

        clip = gui_model.Clipboard.instance()

        try:
            rows = list(expimp.import_channels_str(ty.cast(str, clip.get())))
        except Exception:
            _LOG.exception("import from clipboard error")
            return

        start_num = int(sel[0])
        for chan_num, row in enumerate(rows, start_num):
            chan = self._radio_memory.get_channel(chan_num).clone()
            # do not clean existing rows
            if row.get("freq"):
                try:
                    chan.from_record(row)
                    chan.validate()
                except ValueError:
                    _LOG.exception("import from clipboard error")
                    _LOG.error("chan_num=%d, row=%r", chan_num, row)
                    return

                chan.hide_channel = False
                # do not set bank on paste
                chan.bank = consts.BANK_NOT_SET
                chan.bank_pos = 0
                self._radio_memory.set_channel(chan)

            # stop on range boundary
            if chan_num % 100 == 99:  # noQa: PLR2004
                break

        self.__update_chan_list(None)

    def _show_stats(self) -> None:
        active = sum(
            (1 for c in self._tb_model.data if c and not c.hide_channel),
        )
        self._parent.set_status(f"Active channels: {active}")  # type: ignore

# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
from tkinter import messagebox, ttk

from . import gui_model, model
from .gui_widgets import (
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
        self._chan_group_list = tk.Listbox(pw, selectmode=tk.SINGLE)
        self._chan_group_list.insert(tk.END, *gui_model.CHANNEL_RANGES)
        self._chan_group_list.bind(
            "<<ListboxSelect>>", self.__update_chan_list
        )
        pw.add(self._chan_group_list, weight=0)

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
        self.__update_chan_list(None)

    def _create_channel_list(self, frame: tk.Frame) -> None:
        self._tb_model = gui_model.ChannelsListModel(self._radio_memory)
        ccframe, self._channels_list = build_list_model(frame, self._tb_model)
        ccframe.grid(row=0, column=0, sticky=tk.N + tk.S + tk.E + tk.W)
        self._channels_list.bind(
            "<<TreeviewSelect>>", self.__on_channel_select, add="+"
        )
        self._channels_list.bind("<Delete>", self.__on_channel_delete)

    def __on_channel_select(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._channels_list.selection()
        if not sel:
            return

        chan_num = int(sel[0])
        chan = self._radio_memory.get_channel(chan_num)
        _LOG.debug("chan: %r", chan)

    def __on_channel_delete(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._channels_list.selection()
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
        self.__update_chan_list(None)
        self._channels_list.selection_set(sel)

    def __update_chan_list(self, event: tk.Event | None) -> None:  # type: ignore
        if sel := self._chan_group_list.curselection():  # type: ignore
            selected_range = sel[0]
        else:
            self._tb_model.data = []
            self._channels_list.update_all()
            return

        range_start = selected_range * 100
        self._tb_model.data = [
            self._radio_memory.get_channel(idx)
            for idx in range(range_start, range_start + 100)
        ]
        self._channels_list.update_all()

        if event is not None:
            self._channels_list.yview(0)
            self._channels_list.xview(0)

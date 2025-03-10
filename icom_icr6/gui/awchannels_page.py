# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

"""
Notebook page containing auto written channels.
"""

import logging
import tkinter as tk
import typing as ty
from tkinter import messagebox, ttk

from icom_icr6 import expimp
from icom_icr6.change_manager import ChangeManeger
from icom_icr6.radio_memory import RadioMemory

from . import awchannels_list, dlg_copy, gui_model

_LOG = logging.getLogger(__name__)
_ = ty


class AutoWriteChannelsPage(tk.Frame):
    # TODO: add clear button
    def __init__(self, parent: tk.Widget, cm: ChangeManeger) -> None:
        super().__init__(parent)
        self._parent = parent
        self._change_manager = cm

        frame = tk.Frame(self)
        self._create_fields(frame)
        self._create_channel_list(frame)
        frame.pack(expand=True, fill=tk.BOTH, padx=12, pady=12)

    def update_tab(self, channel_number: int | None = None) -> None:
        # hide canceller in global models
        self._chan_list.set_radio_memory(self._change_manager.rm)
        self._update_channels_list(select=channel_number)

    def select(self, channel_number: int) -> None:
        self._chan_list.selection_set([channel_number])

    def reset(self) -> None:
        self._chan_list.set_radio_memory(self._change_manager.rm)
        self._update_channels_list()

    @property
    def _radio_memory(self) -> RadioMemory:
        return self._change_manager.rm

    def _create_channel_list(self, frame: tk.Frame) -> None:
        self._chan_list = awchannels_list.ChannelsList(
            frame, self._change_manager.rm
        )
        self._chan_list.on_record_selected = self._on_channel_select
        self._chan_list.pack(
            expand=True, fill=tk.BOTH, side=tk.TOP, padx=12, pady=12
        )
        self._chan_list.sheet.bind("<Control-c>", self.__on_channel_copy)

    def _create_fields(self, frame: tk.Frame) -> None:
        fields = tk.Frame(frame)

        self._btn_copy = ttk.Button(
            fields,
            text="Copy channels...",
            command=self._on_btn_copy,
            state="disabled",
        )
        self._btn_copy.pack(side=tk.LEFT, padx=6)

        self._btn_copy = ttk.Button(
            fields,
            text="Remove all...",
            command=self._on_btn_clear,
        )
        self._btn_copy.pack(side=tk.LEFT, padx=6)

        fields.pack(side=tk.TOP, fill=tk.X)

    def _update_channels_list(
        self,
        _event: tk.Event | None = None,  # type: ignore
        select: int | None = None,
    ) -> None:
        self._chan_list.set_data(self._radio_memory.awchannels)
        self._show_stats()
        if select is not None:
            self.after(100, lambda: self._chan_list.selection_set([select]))

    def _on_channel_select(self, rows: list[awchannels_list.RowType]) -> None:
        # change buttons state
        self._btn_copy["state"] = "normal" if rows else "disabled"

        if _LOG.isEnabledFor(logging.DEBUG):
            for row in rows:
                _LOG.debug("chan selected: %r", row.obj)

    def __on_channel_copy(self, _event: tk.Event) -> None:  # type: ignore
        selected = self._chan_list.sheet.get_currently_selected()
        if not selected:
            return

        res = None

        if selected.type_ == "rows":
            if rows := self._chan_list.selected_rows_data():
                channels = (chan for row in rows if (chan := row.obj))
                res = expimp.export_channel_str(channels)

        elif selected.type_ == "cells" and (
            data := self._chan_list.selected_data()
        ):
            res = expimp.export_table_as_string(data).strip()

        if res:
            gui_model.Clipboard.instance().put(res)

    def _on_btn_copy(self) -> None:
        channels = [
            r.obj for r in self._chan_list.selected_rows_data() if r.obj
        ]
        if not channels:
            return

        dlg_copy.CopyChannelsDialog(
            self, self._change_manager, channels, ro=True
        )

    def _on_btn_clear(self) -> None:
        if messagebox.askyesno(
            "Remove autowrite channels",
            "Remove all autowrite channels?\nThis can't be undone.",
            icon=messagebox.WARNING,
        ):
            self._change_manager.rm.clear_awchannels()
            self._update_channels_list()

    def _show_stats(self) -> None:
        active = sum(
            bool(r and (c := r.obj) and not c.hide_channel)
            for r in ty.cast(
                ty.Iterable[awchannels_list.RowType], self._chan_list.data
            )
        )
        self._parent.set_status(f"Channels: {active}")  # type: ignore

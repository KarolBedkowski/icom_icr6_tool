# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

"""
Notebook page containing auto written channels.
"""

import logging
import tkinter as tk
import typing as ty

from icom_icr6 import expimp
from icom_icr6.change_manager import ChangeManeger
from icom_icr6.radio_memory import RadioMemory

from . import gui_awchannlist, gui_model

_LOG = logging.getLogger(__name__)
_ = ty


class AutoWriteChannelsPage(tk.Frame):
    # TODO: add clear button
    def __init__(self, parent: tk.Widget, cm: ChangeManeger) -> None:
        super().__init__(parent)
        self._parent = parent
        self._change_manager = cm

        self._create_channel_list(self)

    def update_tab(self, channel_number: int | None = None) -> None:
        # hide canceller in global models
        self._chan_list.set_region(self._change_manager.rm.region)
        self._update_channels_list(select=channel_number)

    def select(self, channel_number: int) -> None:
        self._chan_list.selection_set([channel_number])

    @property
    def _radio_memory(self) -> RadioMemory:
        return self._change_manager.rm

    def _create_channel_list(self, frame: tk.Frame) -> None:
        self._chan_list = gui_awchannlist.ChannelsList(frame)
        self._chan_list.pack(
            expand=True, fill=tk.BOTH, side=tk.TOP, padx=12, pady=12
        )
        self._chan_list.sheet.bind("<Control-c>", self.__on_channel_copy)

    def _update_channels_list(
        self,
        _event: tk.Event | None = None,  # type: ignore
        select: int | None = None,
    ) -> None:
        self._chan_list.set_data(self._radio_memory.awchannels)
        self._show_stats()
        if select is not None:
            self.after(100, lambda: self._chan_list.selection_set([select]))

    def __on_channel_copy(self, _event: tk.Event) -> None:  # type: ignore
        selected = self._chan_list.sheet.get_currently_selected()
        if not selected:
            return

        res = None

        if selected.type_ == "rows":
            if rows := self._chan_list.selected_rows_data():
                channels = (chan for row in rows if (chan := row.channel))
                res = expimp.export_channel_str(channels)

        elif selected.type_ == "cells" and (
            data := self._chan_list.selected_data()
        ):
            res = expimp.export_table_as_string(data).strip()

        if res:
            gui_model.Clipboard.instance().put(res)

    def _show_stats(self) -> None:
        active = sum(
            bool(r and (c := r.channel) and not c.hide_channel)
            for r in self._chan_list.data
        )
        self._parent.set_status(f"Channels: {active}")  # type: ignore

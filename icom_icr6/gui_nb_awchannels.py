# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty

from . import expimp, gui_awchannlist, gui_model, model

_LOG = logging.getLogger(__name__)
_ = ty


class AutoWriteChannelsPage(tk.Frame):
    def __init__(
        self, parent: tk.Widget, radio_memory: model.RadioMemory
    ) -> None:
        super().__init__(parent)
        self._parent = parent
        self._radio_memory = radio_memory

        self._create_channel_list(self)

    def update_tab(self, radio_memory: model.RadioMemory) -> None:
        self._radio_memory = radio_memory

        # hide canceller in global models
        self._chan_list.set_hide_canceller(
            hide=not radio_memory.is_usa_model()
        )

        self.__update_channels_list(None)

    def _create_channel_list(self, frame: tk.Frame) -> None:
        self._chan_list = gui_awchannlist.ChannelsList(frame)
        self._chan_list.pack(
            expand=True, fill=tk.BOTH, side=tk.TOP, padx=12, pady=12
        )
        self._chan_list.sheet.bind("<Control-c>", self.__on_channel_copy)

    def __update_channels_list(self, _event: tk.Event | None) -> None:  # type: ignore
        data = sorted(self._radio_memory.get_autowrite_channels())
        for idx, ch in enumerate(data):
            ch.number = idx

        self._chan_list.set_data(data)
        self._show_stats()

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

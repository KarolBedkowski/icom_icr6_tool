# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty

from . import consts, expimp, gui_model, model
from .gui_widgets import (
    TableView2,
    TableViewColumn,
    TableViewModelRow,
    UpdateCellResult,
    build_list_model,
)

_LOG = logging.getLogger(__name__)


class AutoWriteChannelsPage(tk.Frame):
    def __init__(
        self, parent: tk.Widget, radio_memory: model.RadioMemory
    ) -> None:
        super().__init__(parent)
        self._parent = parent

        self._radio_memory = radio_memory

        self._create_channel_list(self)

    def set(self, radio_memory: model.RadioMemory) -> None:
        self._radio_memory = radio_memory

        # hide canceller in global models
        cols = self._chan_list["columns"]
        if not radio_memory.is_usa_model():
            cols = [c for c in cols if c not in ("canc", "canc_freq")]

        self._chan_list["displaycolumns"] = cols

        self.__update_channels_list(None)

    def _create_channel_list(self, frame: tk.Frame) -> None:
        self._chan_list_model = RWChannelsListModel(self._radio_memory)
        ccframe, self._chan_list = build_list_model(
            frame, self._chan_list_model
        )
        ccframe.pack(expand=True, fill=tk.BOTH, side=tk.TOP, padx=12, pady=12)

        self._chan_list.bind(
            "<<TreeviewSelect>>", self.__on_channel_select, add="+"
        )
        self._chan_list.bind("<Control-c>", self.__on_channel_copy)

    def __update_channels_list(self, event: tk.Event | None) -> None:  # type: ignore
        data = sorted(self._radio_memory.get_autowrite_channels())
        for idx, ch in enumerate(data):
            ch.number = idx

        self._chan_list_model.data = data  # type: ignore
        self._chan_list.update_all()
        self._show_stats()

        if event is not None:
            self._chan_list.yview(0)
            self._chan_list.xview(0)

    def __on_channel_select(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._chan_list.selection()
        if not sel:
            return

        chan_num = int(sel[0])
        chan = self._chan_list_model.data[chan_num]
        _LOG.debug("chan: %r", chan)

    def __on_channel_copy(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._chan_list.selection()
        if not sel:
            return

        # copy only not-empty data
        channels = (
            chan
            for chan_num in sel
            if (chan := self._chan_list_model.data[int(chan_num)])
        )
        clip = gui_model.Clipboard.instance()
        clip.put(expimp.export_channel_str(channels))

    def _show_stats(self) -> None:
        self._parent.set_status(  # type: ignore
            f"Channels: {len(self._chan_list_model.data)}"
        )


class RWChannelsListModel(gui_model.ChannelsListModel):
    def _columns(self) -> ty.Iterable[TableViewColumn]:
        tvc = TableViewColumn
        return (
            tvc("num", "Num", tk.E, 30),
            tvc("freq", "Freq", tk.E, 80),
            tvc("mode", "Mode", tk.CENTER, 25),
            tvc("af", "AF", tk.CENTER, 25),
            tvc("att", "ATT", tk.CENTER, 25),
            tvc("ts", "TS", tk.CENTER, 40),
            tvc("duplex", "DUP", tk.CENTER, 25),
            tvc("offset", "Offset", tk.E, 60),
            tvc("vsc", "VSC", tk.CENTER, 25),
            tvc("tone", "Tone", tk.CENTER, 30),
            tvc("tsql", "TSQL", tk.E, 40),
            tvc("dtsc", "DTSC", tk.E, 30),
            tvc("polarity", "Polarity", tk.CENTER, 35),
            tvc("canc", "Canceller", tk.CENTER, 30),
            tvc("canc_freq", "Canceller freq", tk.E, 40),
        )

    def _data2iid(self, chan: model.Channel) -> str:
        return str(chan.number)

    def data2row(self, channel: model.Channel | None) -> TableViewModelRow:
        assert channel
        return (
            str(channel.number),
            gui_model.format_freq(channel.freq // 1000),
            consts.MODES[channel.mode],
            gui_model.yes_no(channel.af_filter),
            gui_model.yes_no(channel.attenuator),
            consts.STEPS[channel.tuning_step],
            consts.DUPLEX_DIRS[channel.duplex],
            gui_model.format_freq(channel.offset // 1000)
            if channel.duplex
            else "",
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
            consts.CANCELLER[channel.canceller],
            gui_model.format_freq(channel.canceller_freq * 10),
        )

    def get_editor(
        self,
        row: int,  # noqa: ARG002
        column: int,  # noqa: ARG002
        value: str,  # noqa: ARG002
        parent: TableView2[model.Channel | None],  # noqa: ARG002
    ) -> tk.Widget | None:
        return None

    def update_cell(
        self,
        row: int,  # row # noqa: ARG002
        column: int,  # noqa: ARG002
        value: str | None,  # new value # noqa: ARG002
    ) -> tuple[UpdateCellResult, model.Channel | None]:
        return UpdateCellResult.NOOP, None

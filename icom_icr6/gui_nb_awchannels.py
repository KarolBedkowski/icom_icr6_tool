# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty

from . import gui_model, model
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
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._radio_memory = radio_memory

        self._create_channel_list(self)

    def set(self, radio_memory: model.RadioMemory) -> None:
        self._radio_memory = radio_memory
        self.__fill_channels(None)

    def _create_channel_list(self, frame: tk.Frame) -> None:
        self._tb_model = RWChannelsListModel(self._radio_memory)
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

    def __fill_channels(self, event: tk.Event | None) -> None:  # type: ignore
        data = sorted(self._radio_memory.get_autowrite_channels())
        for idx, ch in enumerate(data):
            ch.number = idx

        self._tb_model.data = data  # type: ignore
        self._channels_content.update_all()

        if event is not None:
            self._channels_content.yview(0)
            self._channels_content.xview(0)

    def __on_channel_select(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._channels_content.selection()
        if not sel:
            return

        chan_num = int(sel[0])
        chan = self._radio_memory.get_channel(chan_num)
        _LOG.debug("chan: %r", chan)


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
        )

    def _data2iid(self, chan: model.Channel) -> str:
        return str(chan.number)

    def data2row(self, channel: model.Channel | None) -> TableViewModelRow:
        assert channel
        return (
            str(channel.number),
            str(channel.freq // 1000),
            model.MODES[channel.mode],
            gui_model.yes_no(channel.af_filter),
            gui_model.yes_no(channel.attenuator),
            model.STEPS[channel.tuning_step],
            model.DUPLEX_DIRS[channel.duplex],
            str(channel.offset // 1000) if channel.duplex else "",
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

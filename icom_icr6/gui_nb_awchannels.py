# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty

from . import consts, expimp, gui_awchannlist, gui_model, model
from .gui_widgets import (
    TableView2,
    TableViewColumn,
    TableViewModelRow,
    UpdateCellResult,
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

    def set(
        self, radio_memory: model.RadioMemory, *, activate: bool = False
    ) -> None:
        _ = activate
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
        rows = self._chan_list.selected_rows()
        if not rows:
            return

        # copy only not-empty data
        channels = (chan for row in rows if (chan := row.channel))
        clip = gui_model.Clipboard.instance()
        clip.put(expimp.export_channel_str(channels, with_bank=False))

    def _show_stats(self) -> None:
        active = sum(
            1 for c in self._chan_list.data if c and not c.hide_channel
        )
        self._parent.set_status(f"Channels: {active}")  # type: ignore


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

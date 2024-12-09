# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from itertools import starmap

from tksheet import EventDataDict, Span

from . import consts, gui_chanlist, gui_genericlist, model

_LOG = logging.getLogger(__name__)


class AWCRow(gui_genericlist.BaseRow):
    COLUMNS = (
        ("channel", "Number", "int"),
        ("freq", "Frequency", "freq"),
        ("mode", "Mode", consts.MODES),
        ("name", "Name", "str"),
        ("af", "AF", "bool"),
        ("att", "ATT", "bool"),  # 5
        ("ts", "Tuning Step", consts.STEPS),
        ("dup", "DUP", consts.DUPLEX_DIRS),
        ("offset", "Offset", "freq"),
        ("vsc", "VSC", "bool"),  # 10
        ("tone_mode", "Tone", consts.TONE_MODES),
        ("tsql_freq", "TSQL", consts.CTCSS_TONES),
        ("dtcs", "DTCS", consts.DTCS_CODES),
        ("polarity", "Polarity", consts.POLARITY),
        ("canceller", "Canceller", consts.CANCELLER),
        ("canceller freq", "Canceller freq", "int"),
    )

    def __init__(self, rownum: int, channel: model.Channel | None) -> None:
        self.channel = channel
        super().__init__(rownum, self._from_channel(channel))

    def set_channel(self, channel: model.Channel) -> None:
        self.channel = channel
        self.data = self._from_channel(channel)

    def __setitem__(self, idx: int, val: object, /) -> None:  # type: ignore
        # immutable list
        return

    def _from_channel(self, channel: model.Channel | None) -> list[object]:
        # valid channel
        if channel and not channel.hide_channel and channel.freq:
            return self._extracts_cols(channel.to_record())

        # empty channel
        return [""] * 16


class ChannelsList(gui_chanlist.ChannelsList):
    _ROW_CLASS = AWCRow

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.sheet.extra_bindings("begin_move_rows", self._on_begin_row_move)

    def set_data(self, data: ty.Iterable[model.Channel | None]) -> None:
        self.sheet.set_sheet_data(list(starmap(AWCRow, enumerate(data))))
        self.sheet.set_all_column_widths()
        for row in range(len(self.sheet.data)):
            self.update_row_state(row)

    def update_row_state(self, row: int) -> None:
        data_row = self.sheet.data[row]
        chan = data_row.channel

        self._set_cell_ro(row, "offset", not chan.duplex)
        self._set_cell_ro(row, "tsql_freq", chan.tone_mode not in (1, 2))

        dtcs = chan.tone_mode in (3, 4)
        self._set_cell_ro(row, "dtcs", not dtcs)
        self._set_cell_ro(row, "polarity", not dtcs)

        self._set_cell_ro(row, "bank_pos", chan.bank == consts.BANK_NOT_SET)
        self._set_cell_ro(row, "canceller", not chan.canceller)
        self._set_cell_ro(row, "canceller freq", not chan.duplex)

    def _configure_col(
        self, column: gui_genericlist.Column, span: Span
    ) -> None:
        colname, _c, values = column
        if isinstance(values, (list, tuple)):
            # show dict-ed value as string
            span.align("center")
        elif values == "bool":
            span.checkbox().align("center")
        else:
            super()._configure_col(column, span)

    def _on_begin_row_move(self, _event: EventDataDict) -> None:
        # prevent moving rows
        raise ValueError

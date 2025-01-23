# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty

from tksheet import EventDataDict, Span

from icom_icr6 import consts, radio_memory

from . import channels_list, genericlist

_LOG = logging.getLogger(__name__)

RowType = channels_list.RowType


class ChannelsList(channels_list.ChannelsList2):
    COLUMNS: ty.ClassVar[channels_list.ColumnsDef] = (
        ("channel", "Number", "int"),
        ("freq", "Frequency", "freq"),
        ("mode", "Mode", consts.MODES),
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

    def __init__(
        self, parent: tk.Widget, rm: radio_memory.RadioMemory
    ) -> None:
        super().__init__(parent, rm)
        self.sheet.extra_bindings("begin_move_rows", self._on_begin_row_move)

    def _update_row_state(self, row: int) -> None:
        data_row = self.sheet.data[row]
        chan = data_row.obj

        self._set_cell_ro(row, "offset", not chan.duplex)
        self._set_cell_ro(row, "tsql_freq", chan.tone_mode not in (1, 2))

        dtcs = chan.tone_mode in (3, 4)
        self._set_cell_ro(row, "dtcs", not dtcs)
        self._set_cell_ro(row, "polarity", not dtcs)

        self._set_cell_ro(row, "bank_pos", chan.bank == consts.BANK_NOT_SET)
        self._set_cell_ro(row, "canceller", not chan.canceller)
        self._set_cell_ro(row, "canceller freq", chan.canceller != 1)

    def _configure_col(self, column: genericlist.Column, span: Span) -> None:
        _colname, _c, values = column
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

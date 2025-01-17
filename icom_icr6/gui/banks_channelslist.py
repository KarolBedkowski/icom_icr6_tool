# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty

from tksheet import functions

from icom_icr6 import consts, radio_memory

from . import channels_list

_LOG = logging.getLogger(__name__)
_SKIPS: ty.Final = ["", "S", "P"]

RowType = channels_list.RowType


class ChannelsList(channels_list.ChannelsList2):
    COLUMNS: ty.ClassVar[channels_list.ColumnsDef] = (
        ("bank_pos", "Pos", "int"),
        ("channel", "Channel", "int"),
        ("freq", "Frequency", "freq"),
        ("mode", "Mode", consts.MODES),
        ("name", "Name", "str"),
        ("af", "AF", "bool"),
        ("att", "ATT", "bool"),  # 5
        ("ts", "Tuning Step", consts.STEPS),
        ("dup", "DUP", consts.DUPLEX_DIRS),
        ("offset", "Offset", "freq"),
        ("skip", "Skip", _SKIPS),
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
        self.bank: int | None = None

    def set_bank(self, bank: int | None) -> None:
        self.bank = bank

    def update_row_state(self, row: int) -> None:
        super().update_row_state(row)
        # make col "channel" always rw
        functions.set_readonly(
            self.sheet.MT.cell_options, (row, 2), readonly=False
        )

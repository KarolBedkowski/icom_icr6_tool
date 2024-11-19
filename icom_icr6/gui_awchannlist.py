# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import typing as ty

from tksheet import (
    int_formatter,
    num2alpha,
)

from . import consts, gui_chanlist, model

_LOG = logging.getLogger(__name__)


class AWCRow(gui_chanlist.BaseRow):
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
        ("dtsc", "DTSC", consts.DTCS_CODES),
        ("polarity", "Polarity", consts.POLARITY),
        ("canceller", "Canceller", consts.CANCELLER),
        ("canceller freq", "Canceller freq", "int"),
    )

    def __init__(self, channel: model.Channel | None) -> None:
        self.channel = channel
        super().__init__(self._from_channel(channel))

    def set_channel(self, channel: model.Channel) -> None:
        self.channel = channel
        self.data = self._from_channel(channel)

    def __hash__(self) -> int:
        return hash(
            self.__class__.__name__ + str(self.data[0] if self.data else None)
        )

    def __setitem__(self, idx: int, val: object, /) -> None:  # type: ignore
        # immutable list
        return

    def _from_channel(self, channel: model.Channel | None) -> list[object]:
        # valid channel
        if channel and not channel.hide_channel and channel.freq:
            data = channel.to_record()
            return [data[col] for col, *_ in self.COLUMNS]

        # empty channel
        return [""] * 16


class ChannelsList(gui_chanlist.ChannelsList[AWCRow]):
    _ROW_CLASS = AWCRow

    def set_data(self, data: ty.Iterable[model.Channel | None]) -> None:
        self.sheet.set_sheet_data(list(map(AWCRow, data)))
        self.sheet.set_all_column_widths()
        for row in range(len(self.sheet.data)):
            self.update_row_state(row)

    def update_row_state(self, row: int) -> None:
        data_row = self.sheet.data[row]
        chan = data_row.channel

        self._set_cell_ro(row, "offset", not chan.duplex)
        self._set_cell_ro(row, "tsql_freq", chan.tone_mode not in (1, 2))

        dtsc = chan.tone_mode in (3, 4)
        self._set_cell_ro(row, "dtsc", not dtsc)
        self._set_cell_ro(row, "polarity", not dtsc)

        self._set_cell_ro(row, "bank_pos", chan.bank == consts.BANK_NOT_SET)
        self._set_cell_ro(row, "canceller", not chan.canceller)
        self._set_cell_ro(row, "canceller freq", not chan.duplex)

    def _configure(self) -> None:
        self.sheet.headers([c[1] for c in self.columns])

        for idx, (colname, _c, values) in enumerate(self.columns):
            col = self.sheet[num2alpha(idx)]
            if values == "str":
                continue

            if values == "int":
                col.format(int_formatter(invalid_value="")).align("right")

            elif values == "bool":
                col.checkbox().align("center")

            elif values == "freq":
                col.format(
                    int_formatter(
                        format_function=gui_chanlist.to_int,
                        to_str_function=gui_chanlist.format_freq,
                        invalid_value="",
                    )
                ).align("right")

            elif isinstance(values, (list, tuple)):
                # show dict-ed value as string
                col.align("center")

            else:
                _LOG.error("unknown column %d: %s", idx, colname)

        self.sheet.row_index(0)
        self.sheet.hide_columns(0)

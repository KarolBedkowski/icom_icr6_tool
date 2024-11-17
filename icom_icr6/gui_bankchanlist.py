# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from collections import UserList

from tksheet import (
    EventDataDict,
    Sheet,
    functions,
    int_formatter,
    num2alpha,
)

from . import consts, gui_chanlist, model

_LOG = logging.getLogger(__name__)


class BLRow(UserList[object]):
    COLUMNS = (
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
        ("skip", "Skip", consts.SKIPS),
        ("vsc", "VSC", "bool"),  # 10
        ("tone_mode", "Tone", consts.TONE_MODES),
        ("tsql_freq", "TSQL", consts.CTCSS_TONES),
        ("dtsc", "DTSC", consts.DTCS_CODES),
        ("polarity", "Polarity", consts.POLARITY),
        ("canceller", "Canceller", consts.CANCELLER),
        ("canceller freq", "Canceller freq", "int"),
    )

    def __init__(self, bank_pos: int, channel: model.Channel | None) -> None:
        self.bank_pos = bank_pos
        self.channel = channel
        super().__init__(self._from_channel(channel))

    def set_channel(self, channel: model.Channel) -> None:
        self.channel = channel
        self.data = self._from_channel(channel)

    def __hash__(self) -> int:
        return hash(
            self.__class__.__name__ + str(self.data[0] if self.data else None)
        )

    def __setitem__(self, idx: int, val: object) -> None:
        if val == self.data[idx]:
            return

        chan = self.channel
        if not chan:
            return

        col = self.COLUMNS[idx][0]

        if (not chan.freq or chan.hide_channel) and idx != 1:
            return

        match col:
            case "bank_pos":
                return

            case "freq":  # freq
                if val:
                    assert isinstance(val, int)

                    if not chan.freq or chan.hide_channel:
                        chan.mode = model.default_mode_for_freq(val)

                chan.freq = val or 0  # type: ignore
                chan.hide_channel = not val
                self.data = self._from_channel(chan)
                return

        data = chan.to_record()
        if data[col] == val:
            return

        try:
            chan.from_record({col: val})
        except Exception:
            _LOG.exception("from record error: %r=%r", col, val)

        super().__setitem__(idx, val)

    def _from_channel(self, channel: model.Channel | None) -> list[object]:
        if (
            not channel
            or channel.hide_channel
            or not channel.freq
            or channel.bank == consts.BANK_NOT_SET
        ):
            return [self.bank_pos, *([""] * 17)]

        data = channel.to_record()
        return [self.bank_pos, *(data[col] for col, *_ in self.COLUMNS[1:])]

    def delete(self) -> None:
        if chan := self.channel:
            chan.bank = consts.BANK_NOT_SET
            self.data = self._from_channel(chan)


class NewChannelCallback(ty.Protocol):
    def __call__(self) -> model.Channel: ...


class ChangeChannelCallback(ty.Protocol):
    def __call__(self, channum: int, bank_pos: int) -> model.Channel: ...


class ChannelsList(gui_chanlist.ChannelsList[BLRow]):
    _ROW_CLASS = BLRow

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.on_new_channel: NewChannelCallback | None = None
        self.on_change_channel: ChangeChannelCallback | None = None
        self.bank: int | None = None

    def set_bank(self, bank: int | None) -> None:
        self.bank = bank

    def set_data(self, data: ty.Iterable[model.Channel]) -> None:
        self.sheet.set_sheet_data(
            [BLRow(idx, chan) for idx, chan in enumerate(data)]
        )
        self.sheet.set_all_column_widths()
        for row in range(len(self.sheet.data)):
            self.update_row_state(row)

    def _on_validate_edits(self, event: EventDataDict) -> object:
        if event.eventname != "end_edit_table" or self.bank is None:
            return None

        _LOG.debug("_on_validate_edits: %r", event)

        column = self.columns[event.column + 1]  # FIXME: visible cols
        row = self.sheet.data[event.row]
        chan = row.channel
        value = event.value

        _LOG.debug("_on_validate_edits: chan=%r", chan)

        if chan is None:
            match column[0]:
                case "channel":
                    assert self.on_change_channel
                    chan = self.on_change_channel(int(value), event.row)

                case "freq":
                    assert self.on_new_channel
                    # TODO: handle error
                    chan = self.on_new_channel()
                    chan.freq = int(value)
                    chan.hide_channel = False
                case _:
                    return None

            chan.bank = self.bank
            chan.bank_pos = event.row
            row.set_channel(chan)

        return super()._on_validate_edits(event)

    def update_row_state(self, row: int) -> None:
        functions.set_readonly(
            self.sheet.MT.cell_options, (row, 3), readonly=False
        )

    # def update_row_state(self, row: int) -> None:
    #     """Set state of other cells in row (readony)."""
    #     data_row = self.sheet.data[row]
    #     chan = data_row.channel

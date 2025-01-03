# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import itertools
import logging
import tkinter as tk
import typing as ty
from contextlib import suppress

from tksheet import functions

from . import consts, gui_chanlist, gui_genericlist, model

_LOG = logging.getLogger(__name__)

_SKIPS: ty.Final = ["", "S", "P"]


class BLRow(gui_genericlist.BaseRow):
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
        ("skip", "Skip", _SKIPS),
        ("vsc", "VSC", "bool"),  # 10
        ("tone_mode", "Tone", consts.TONE_MODES),
        ("tsql_freq", "TSQL", consts.CTCSS_TONES),
        ("dtcs", "DTCS", consts.DTCS_CODES),
        ("polarity", "Polarity", consts.POLARITY),
        ("canceller", "Canceller", consts.CANCELLER),
        ("canceller freq", "Canceller freq", "int"),
    )

    def __init__(self, bank_pos: int, channel: model.Channel | None) -> None:
        # channel to set
        self.new_channel: int | None = None
        # new freq to set (if not channel, find free channel and set)
        self.new_freq: int | None = None
        self.channel = channel
        self.rownum = bank_pos

        super().__init__(bank_pos, self._from_channel(channel))

    def set_channel(self, channel: model.Channel) -> None:
        self.channel = channel
        self.data = self._from_channel(channel)

    def __setitem__(self, idx: int, val: object, /) -> None:  # type: ignore
        if val == self.data[idx]:
            return

        chan = self.channel
        col = self.COLUMNS[idx][0]

        match col:
            case "channel":
                # change channel
                with suppress(ValueError, TypeError):
                    channum = int(val)  # type: ignore
                    # valid channel number - change
                    if not chan or channum != chan.number:
                        self.new_channel = channum

                return

            case "freq":  # freq
                try:
                    freq = int(val)  # type: ignore
                except (ValueError, TypeError):
                    return

                # valid frequency
                # if not chan - create new
                if not chan or not chan.freq or chan.hide_channel:
                    self.new_freq = freq
                    return

                # otherwise - update existing by standard way

        # if chan exists and is valid - update
        if chan and chan.freq and not chan.hide_channel:
            chan = self._make_clone()
            try:
                chan.from_record({col: val})
            except Exception:
                _LOG.exception("from record error: %r=%r", col, val)

            super().__setitem__(idx, val)

    def _make_clone(self) -> model.Channel:
        """Make copy of channel for updates."""
        assert self.channel

        if not self.updated:
            self.updated = True
            self.channel = self.channel.clone()

        return self.channel

    def _from_channel(self, channel: model.Channel | None) -> list[object]:
        # valid channel
        if (
            channel
            and not channel.hide_channel
            and channel.freq
            and channel.bank != consts.BANK_NOT_SET
        ):
            data = channel.to_record()
            return [
                self.rownum,
                *(data[col] for col, *_ in self.COLUMNS[1:]),
            ]

        # empty channel
        return [
            self.rownum,
            self.new_channel if self.new_channel is not None else "",
            self.new_freq or "",
            *([""] * 15),
        ]


class ChannelsList(gui_chanlist.ChannelsList):
    _ROW_CLASS = BLRow

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.bank: int | None = None

    def set_bank(self, bank: int | None) -> None:
        self.bank = bank

    def set_data(self, data: ty.Iterable[model.Channel | None]) -> None:
        self.sheet.set_sheet_data(
            list(itertools.starmap(BLRow, enumerate(data)))
        )
        self.sheet.set_all_column_widths()
        for row in range(len(self.sheet.data)):
            self.update_row_state(row)

    def update_row_state(self, row: int) -> None:
        super().update_row_state(row)
        # make col "channel" always rw
        functions.set_readonly(
            self.sheet.MT.cell_options, (row, 2), readonly=False
        )

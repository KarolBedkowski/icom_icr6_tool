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

from . import consts, model

_LOG = logging.getLogger(__name__)


COLUMNS = [
    ("channel", "Num"),
    ("freq", "Frequency"),
    ("mode", "Mode"),
    ("name", "Name"),
    ("af", "AF"),
    ("att", "ATT"),
    ("ts", "Tuning Step"),
    ("dup", "DUP"),
    ("offset", "Offset"),
    ("skip", "Skip"),
    ("vsc", "VSC"),
    ("tone_mode", "Tone"),
    ("tsql_freq", "TSQL"),
    ("dtsc", "DTSC"),
    ("polarity", "Polarity"),
    ("bank", "Bank"),
    ("bank_pos", "Bank pos"),
    ("canceller", "Canceller"),
    ("canceller freq", "Canceller freq"),
]


class Row(UserList[object]):
    def __init__(self, channel: model.Channel) -> None:
        self.channel = channel
        super().__init__(self._from_channel(channel))

    def __setitem__(self, idx: int, val: object) -> None:
        if val == self.data[idx]:
            return

        chan = self.channel
        col = COLUMNS[idx][0]

        if (not chan.freq or chan.hide_channel) and idx != 1:
            return

        match col:
            case "number":
                return

            case "freq":  # freq
                if val is None:
                    chan.freq = 0
                    chan.hide_channel = True
                    self.data = self._from_channel(chan)
                    return

                assert isinstance(val, int)
                chan.freq = val
                chan.hide_channel = False
                chan.mode = model.default_mode_for_freq(chan.freq)
                self.data = self._from_channel(chan)
                return

        # TODO: optimize
        data = chan.to_record()
        if data[col] == val:
            return

        data[col] = val
        chan.from_record(data)

        super().__setitem__(idx, val)

    def _from_channel(self, channel: model.Channel) -> list[object]:
        if channel is None:
            return [""] * 19

        if channel.hide_channel or not channel.freq:
            return [channel.number, *([""] * 18)]

        data = channel.to_record()
        return [data[col] for col, *_ in COLUMNS]

    def delete(self) -> None:
        self.channel.hide_channel = True
        self.channel.freq = 0
        self.data = self._from_channel(self.channel)


def to_int(o: object, **_kwargs: object) -> int:
    if isinstance(o, int):
        return o

    if isinstance(o, str):
        return int(o.replace(" ", ""))

    return int(o)  # type: ignore


def format_freq(freq: int, **_kwargs: object) -> str:
    return f"{freq:_}".replace("_", " ")


class ChannelsList(tk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.sheet = Sheet(
            self, data=[], default_column_width=40, alternate_color="#E2EAF4"
        )
        self.sheet.enable_bindings("all")
        self.sheet.edit_validation(self._on_validate_edits)
        self.sheet.bind("<<SheetModified>>", self._on_sheet_modified)
        self.sheet.pack(expand=True, fill=tk.BOTH, side=tk.TOP)
        self.sheet.bind("<<SheetSelect>>", self._on_sheet_select)
        self.sheet.extra_bindings("begin_delete", self._on_delete)

        self.columns = COLUMNS
        self._configure()
        self.on_record_update: (
            ty.Callable[[ty.Collection[Row]], None] | None
        ) = None
        self.on_record_selected: ty.Callable[[list[Row]], None] | None = None

    def set_data(self, data: ty.Iterable[model.Channel]) -> None:
        self.sheet.set_sheet_data(list(map(Row, data)))
        self.sheet.set_all_column_widths()
        for row in range(len(self.sheet.data)):
            self._update_row_states(row)

    def _setup_dropbox(self, col: int, values: list[str]) -> None:
        self.sheet[num2alpha(col)].dropdown(
            values=values,
            state="",
        ).align("center")

    def _setup_dropbox_bank(self, col: int) -> None:
        values: list[str] = ["", *consts.BANK_NAMES]
        self.sheet[num2alpha(col)].dropdown(
            values=values,
            state="",
        ).align("center")

    def _configure(self) -> None:
        self.sheet.headers([c[0] for c in self.columns])

        self.sheet[num2alpha(0)].format(int_formatter()).align("right")
        self.sheet[num2alpha(1)].format(
            int_formatter(
                format_function=to_int,
                to_str_function=format_freq,
                invalid_value="",
            )
        ).align("right")
        self._setup_dropbox(2, consts.MODES)
        self.sheet[num2alpha(4)].checkbox().align("center")
        self.sheet[num2alpha(5)].checkbox().align("center")
        self._setup_dropbox(6, consts.STEPS)
        self._setup_dropbox(7, consts.DUPLEX_DIRS)
        self.sheet[num2alpha(8)].format(int_formatter(invalid_value="")).align(
            "right"
        )
        self._setup_dropbox(9, consts.SKIPS)
        self.sheet[num2alpha(10)].checkbox().align("center")
        self._setup_dropbox(11, consts.TONE_MODES)
        self._setup_dropbox(12, consts.CTCSS_TONES)
        self._setup_dropbox(13, consts.DTCS_CODES)
        self._setup_dropbox(14, consts.POLARITY)
        self._setup_dropbox_bank(15)
        self.sheet[num2alpha(16)].format(
            int_formatter(invalid_value="")
        ).align("center")
        self._setup_dropbox(17, consts.CANCELLER)
        self.sheet[num2alpha(18)].format(
            int_formatter(invalid_value="")
        ).align("right")

        self.sheet.row_index(0)
        self.sheet.hide_columns(0)

    def _on_sheet_modified(self, event: EventDataDict) -> None:
        # if event.eventname == "edit_table":
        #    return

        _LOG.debug("_on_sheet_modified: %r", event)

        # if not self.on_record_update or not event.cells.table:
        #    return

        #        for r, _c in event.cells.table:
        #            row = self.sheet.data[r]

        # TODO: distinct
        data = [self.sheet.data[r] for (r, _c) in event.cells.table]

        for r, _c in event.cells.table:
            self._update_row_states(r)

        if data and self.on_record_update:
            self.on_record_update(data)

    def _on_validate_edits(self, event: EventDataDict) -> object:
        if event.eventname != "end_edit_table":
            return None

        _LOG.debug("_on_validate_edits: %r", event)

        column = self.columns[event.column + 1]  # FIXME: visible cols
        row = self.sheet.data[event.row]
        value = event.value

        try:
            match column[0]:
                case "freq":
                    return model.fix_frequency(int(value))

                case "name":
                    return model.fix_name(value)

                case "offset":
                    if not row.duplex:
                        return None

                    assert isinstance(value, int)
                    return max(min(value, consts.MAX_OFFSET), 0)

                case "cf":
                    assert isinstance(value, int)
                    return max(
                        min((value // 10) * 10, consts.CANCELLER_MAX_FREQ),
                        consts.CANCELLER_MIN_FREQ,
                    )

                case "bank_pos":
                    # TODO: validate
                    return max(min(value, 99), 0)

        except ValueError:
            return None

        return event.value

    def _on_sheet_select(self, event: EventDataDict) -> None:
        _LOG.debug("_on_sheet_select: %r", event)
        row, col = event.selected.row, event.selected.column
        column = self.columns[col + 1]  # FIXME: visible cols
        col += 1
        data_row = self.sheet.data[row]

        if not data_row[1] and col != 1:
            functions.set_readonly(
                self.sheet.MT.cell_options, (row, col), readonly=True
            )
            return

        functions.set_readonly(
            self.sheet.MT.cell_options, (row, col), readonly=False
        )
        if column[0] == "ts":
            self.sheet.set_dropdown_values(
                row,
                col,
                values=model.tuning_steps_for_freq(data_row[1]),
            )  # freq

        if self.on_record_selected:
            sel_box = event.selected.box
            rows = [
                self.sheet.data[r]
                for r in range(sel_box.from_r, sel_box.upto_r)
            ]
            self.on_record_selected(rows)

    def selected_rows(self) -> list[Row]:
        return [
            self.sheet.data[r]
            for r in self.sheet.get_selected_rows(get_cells_as_rows=True)
        ]

    def _on_delete(self, event: EventDataDict) -> None:
        data = []
        if event.selected.type_ == "rows":
            box = event.selected.box
            for r in range(box.from_r, box.upto_r):
                row = self.sheet.data[r]
                row.delete()
                data.append(row)
                self._update_row_states(r)

        elif event.selected.type_ == "cells":
            r = event.selected.row
            self.sheet[r, event.selected.column + 1].data = ""
            self._update_row_states(r)
            data.append(self.sheet.data[r])

        if data and self.on_record_update:
            self.on_record_update(data)

    def _update_row_states(self, row: int) -> None:
        data_row = self.sheet.data[row]
        chan = data_row.channel
        self.sheet.highlight_cells(
            row, column=8, fg="black" if chan.duplex else "gray"
        )
        self.sheet.highlight_cells(
            row, column=12, fg="black" if chan.tone_mode in (1, 2) else "gray"
        )
        self.sheet.highlight_cells(
            row, column=13, fg="black" if chan.tone_mode in (3, 4) else "gray"
        )
        self.sheet.highlight_cells(
            row, column=14, fg="black" if chan.tone_mode in (3, 4) else "gray"
        )
        self.sheet.highlight_cells(
            row,
            column=16,
            fg="black" if chan.bank != consts.BANK_NOT_SET else "gray",
        )

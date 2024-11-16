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
    ("att", "ATT"),  # 5
    ("ts", "Tuning Step"),
    ("dup", "DUP"),
    ("offset", "Offset"),
    ("skip", "Skip"),
    ("vsc", "VSC"),  # 10
    ("tone_mode", "Tone"),
    ("tsql_freq", "TSQL"),
    ("dtsc", "DTSC"),
    ("polarity", "Polarity"),
    ("bank", "Bank"),  # 15
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
                if not val:
                    chan.freq = 0
                    chan.hide_channel = True
                    self.data = self._from_channel(chan)
                    return

                assert isinstance(val, int)
                if not chan.freq:
                    chan.mode = model.default_mode_for_freq(chan.freq)

                chan.freq = val
                chan.hide_channel = False
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


@ty.runtime_checkable
class BankPosValidator(ty.Protocol):
    def __call__(
        self,
        bank: int | str,
        channum: int,
        bank_pos: int,
        *,
        try_set_free_slot: bool = False,
    ) -> int: ...


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
        self.on_channel_bank_validate: BankPosValidator | None = None

    @property
    def data(self) -> ty.Iterable[model.Channel]:
        for r in self.sheet.data:
            yield r.channel

    def set_hide_canceller(self, *, hide: bool) -> None:
        if hide:
            self.sheet.hide_columns((16, 17))
        else:
            self.sheet.show_columns((16, 17))

    def set_data(self, data: ty.Iterable[model.Channel]) -> None:
        self.sheet.set_sheet_data(list(map(Row, data)))
        self.sheet.set_all_column_widths()
        for row in range(len(self.sheet.data)):
            self._update_row_states(row)

    def selection(self) -> set[int]:
        return self.sheet.get_selected_rows(get_cells_as_rows=True)  # type: ignore

    def selection_set(self, sel: ty.Iterable[int]) -> None:
        for r in sel:
            self.sheet.select_row(r)
            self.sheet.set_xview(r)

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
        # bank pos
        self.sheet[num2alpha(16)].format(
            int_formatter(invalid_value="")
        ).align("center")
        self._setup_dropbox(17, consts.CANCELLER)
        # canceller
        self.sheet[num2alpha(18)].format(
            int_formatter(invalid_value="")
        ).align("right")

        self.sheet.row_index(0)
        self.sheet.hide_columns(0)

    def _on_sheet_modified(self, event: EventDataDict) -> None:
        # if event.eventname == "edit_table":
        #    return

        _LOG.debug("_on_sheet_modified: %r", event)

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
        chan = row.channel
        value = event.value

        try:
            match column[0]:
                case "freq":
                    value = model.fix_frequency(int(value))

                case "name":
                    value = model.fix_name(value)

                case "offset":
                    if off := int(value):
                        value = max(
                            min(off, consts.MAX_OFFSET), consts.MIN_OFFSET
                        )

                case "canceller freq":
                    # round frequency to 10kHz
                    freq = (int(value) // 10) * 10
                    value = max(
                        min(freq, consts.CANCELLER_MAX_FREQ),
                        consts.CANCELLER_MIN_FREQ,
                    )
                case "bank":
                    if chan.bank != value and self.on_channel_bank_validate:
                        # change bank
                        row[16] = self.on_channel_bank_validate(
                            value,
                            chan.number,
                            0,
                            try_set_free_slot=True,
                        )

                case "bank_pos":
                    # TODO: validate
                    # TODO: refresh all records
                    value = max(min(int(value), 99), 0)
                    if self.on_channel_bank_validate:
                        value = self.on_channel_bank_validate(
                            chan.bank, chan.number, value
                        )

        except ValueError:
            _LOG.exception("_on_validate_edits: %r", value)
            return None

        return value

    def _on_sheet_select(self, event: EventDataDict) -> None:
        _LOG.debug("_on_sheet_select: %r", event)
        if not event.selected:
            return

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
        """Set state of other cells in row (readony)."""
        data_row = self.sheet.data[row]
        chan = data_row.channel
        self.sheet.highlight_cells(
            row, column=8, fg="black" if chan.duplex else "gray"
        )

        row_is_readonly = not chan.freq or chan.hide_channel
        for c in range(2, len(COLUMNS)):
            functions.set_readonly(
                self.sheet.MT.cell_options, (row, c), readonly=row_is_readonly
            )

        self._set_cell_ro(row, 12, chan.tone_mode not in (1, 2))

        dtsc = chan.tone_mode in (3, 4)
        self._set_cell_ro(row, 13, not dtsc)
        self._set_cell_ro(row, 14, not dtsc)

        self._set_cell_ro(row, 16, chan.bank == consts.BANK_NOT_SET)
        self._set_cell_ro(row, 18, not chan.canceller)
        self._set_cell_ro(row, 8, not chan.duplex)

        # ts
        self.sheet.set_dropdown_values(
            row,
            6,
            values=model.tuning_steps_for_freq(chan.freq),
        )

    def _set_cell_ro(self, row: int, col: int, readonly: object) -> None:
        ro = bool(readonly)

        self.sheet.highlight_cells(
            row, column=col, fg="gray" if ro else "black"
        )
        functions.set_readonly(
            self.sheet.MT.cell_options, (row, col), readonly=ro
        )

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
    Span,
    functions,
    int_formatter,
    num2alpha,
)

from . import consts, model

_LOG = logging.getLogger(__name__)


class Row(UserList[object]):
    COLUMNS = (
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
    )

    def __init__(self, channel: model.Channel) -> None:
        self.channel = channel
        super().__init__(self._from_channel(channel))

    def __setitem__(self, idx: int, val: object) -> None:
        if val == self.data[idx]:
            return

        chan = self.channel
        col = self.COLUMNS[idx][0]

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
                if not chan.freq or chan.hide_channel:
                    chan.mode = model.default_mode_for_freq(val)

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
        return [data[col] for col, *_ in self.COLUMNS]

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
class RecordActionCallback(ty.Protocol):
    def __call__(
        self,
        action: str,
        rows: list[Row],
    ) -> None: ...


@ty.runtime_checkable
class RecordSelctedCallback(ty.Protocol):
    def __call__(
        self,
        rows: list[Row],
    ) -> None: ...


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
    _ROW_CLASS = Row

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

        self.columns = self._ROW_CLASS.COLUMNS
        self.colmap = {
            name: idx for idx, (name, *_) in enumerate(self.columns)
        }
        self._configure()

        self.on_record_update: RecordActionCallback | None = None
        self.on_record_selected: RecordSelctedCallback | None = None
        self.on_channel_bank_validate: BankPosValidator | None = None

    @property
    def data(self) -> ty.Iterable[model.Channel | None]:
        for r in self.sheet.data:
            yield r.channel

    def set_hide_canceller(self, *, hide: bool) -> None:
        canc_columns = [
            self.colmap[c] - 1 for c in ("canceller", "canceller freq")
        ]
        if hide:
            self.sheet.hide_columns(canc_columns)
        else:
            self.sheet.show_columns(canc_columns)

    def set_data(self, data: ty.Iterable[model.Channel]) -> None:
        self.sheet.set_sheet_data(list(map(Row, data)))
        self.sheet.set_all_column_widths()
        for row in range(len(self.sheet.data)):
            self.update_row_state(row)

    def selection(self) -> set[int]:
        return self.sheet.get_selected_rows(get_cells_as_rows=True)  # type: ignore

    def selection_set(self, sel: ty.Iterable[int]) -> None:
        for r in sel:
            self.sheet.select_row(r)
            self.sheet.set_xview(r)

    def _col(self, column: str) -> Span:
        return self.sheet[num2alpha(self.colmap[column])]

    def _setup_dropbox(self, column: str, values: list[str]) -> None:
        col = self.colmap[column]
        self.sheet[num2alpha(col)].dropdown(
            values=values,
            state="",
        ).align("center")

    def _setup_dropbox_bank(self, column: str) -> None:
        col = self.colmap[column]
        values: list[str] = ["", *consts.BANK_NAMES]
        self.sheet[num2alpha(col)].dropdown(
            values=values,
            state="",
        ).align("center")

    def _configure(self) -> None:
        self.sheet.headers([c[0] for c in self.columns])

        self._col("channel").format(int_formatter()).align("right")
        self._col("freq").format(
            int_formatter(
                format_function=to_int,
                to_str_function=format_freq,
                invalid_value="",
            )
        ).align("right")
        self._setup_dropbox("mode", consts.MODES)
        self._col("af").checkbox().align("center")
        self._col("att").checkbox().align("center")
        self._setup_dropbox("ts", consts.STEPS)
        self._setup_dropbox("dup", consts.DUPLEX_DIRS)
        self._col("offset").format(int_formatter(invalid_value="")).align(
            "right"
        )
        self._setup_dropbox("skip", consts.SKIPS)
        self._col("vsc").checkbox().align("center")
        self._setup_dropbox("tone_mode", consts.TONE_MODES)
        self._setup_dropbox("tsql_freq", consts.CTCSS_TONES)
        self._setup_dropbox("dtsc", consts.DTCS_CODES)
        self._setup_dropbox("polarity", consts.POLARITY)
        self._setup_dropbox_bank("bank")
        # bank pos
        self._col("bank_pos").format(int_formatter(invalid_value="")).align(
            "center"
        )
        self._setup_dropbox("canceller", consts.CANCELLER)
        # canceller
        self._col("canceller freq").format(
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
            self.update_row_state(r)

        if data and self.on_record_update:
            self.on_record_update("update", data)

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
                self.update_row_state(r)

            if data and self.on_record_update:
                self.on_record_update("delete", data)

        elif event.selected.type_ == "cells":
            r = event.selected.row
            self.sheet[r, event.selected.column + 1].data = ""
            self.update_row_state(r)
            data.append(self.sheet.data[r])

            if data and self.on_record_update:
                self.on_record_update("update", data)

    def update_row_state(self, row: int) -> None:
        """Set state of other cells in row (readony)."""
        data_row = self.sheet.data[row]
        chan = data_row.channel

        row_is_readonly = not chan.freq or chan.hide_channel
        for c in range(2, len(self.columns)):
            functions.set_readonly(
                self.sheet.MT.cell_options, (row, c), readonly=row_is_readonly
            )

        self._set_cell_ro(row, "offset", not chan.duplex)
        self._set_cell_ro(row, "tsql_freq", chan.tone_mode not in (1, 2))

        dtsc = chan.tone_mode in (3, 4)
        self._set_cell_ro(row, "dtsc", not dtsc)
        self._set_cell_ro(row, "polarity", not dtsc)

        self._set_cell_ro(row, "bank_pos", chan.bank == consts.BANK_NOT_SET)
        self._set_cell_ro(row, "canceller", not chan.canceller)
        self._set_cell_ro(row, "canceller freq", not chan.duplex)

        # ts
        self.sheet.set_dropdown_values(
            row,
            self.colmap["ts"],
            values=model.tuning_steps_for_freq(chan.freq),
        )

    def _set_cell_ro(self, row: int, col: int | str, readonly: object) -> None:
        if isinstance(col, str):
            col = self.colmap[col]

        ro = bool(readonly)

        self.sheet.highlight_cells(
            row, column=col, fg="gray" if ro else "black"
        )
        functions.set_readonly(
            self.sheet.MT.cell_options, (row, col), readonly=ro
        )

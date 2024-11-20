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
_BANKS = ["", *consts.BANK_NAMES]


class BaseRow(UserList[object]):
    COLUMNS: ty.ClassVar[
        ty.Sequence[tuple[str, str, str | ty.Collection[str]]]
    ] = ()


class Row(BaseRow):
    COLUMNS = (
        ("idx", "Num", "int"),
        ("name", "Name", "str"),
        ("start", "Start", "freq"),
        ("end", "End", "freq"),
        ("ts", "Tuning Step", consts.STEPS),
        ("mode", "Mode", consts.MODES),
        ("att", "ATT", consts.ATTENUATOR),
    )

    def __init__(self, se: model.ScanEdge) -> None:
        self.se = se
        super().__init__(self._from_scanedge(se))

    def __hash__(self) -> int:
        return hash(
            self.__class__.__name__ + str(self.data[0] if self.data else None)
        )

    def __setitem__(self, idx: int, val: object, /) -> None:  # type: ignore
        if val == self.data[idx]:
            return

        se = self.se
        col = self.COLUMNS[idx][0]
        match col:
            case "idx":
                return

            case "start":  # freq
                se.start = val or 0  # type: ignore
                self.data = self._from_scanedge(se)
                return

            case "end":  # freq
                se.end = val or 0  # type: ignore
                self.data = self._from_scanedge(se)
                return

        data = se.to_record()
        if data[col] == val:
            return

        try:
            se.from_record({col: val})
        except Exception:
            _LOG.exception(
                "update scanedge from record error: %r=%r", col, val
            )
            return

        super().__setitem__(idx, val)

    def _from_scanedge(self, se: model.ScanEdge) -> list[object]:
        data = se.to_record()
        return [data[col] for col, *_ in self.COLUMNS]


def to_int(o: object, **_kwargs: object) -> int:
    if isinstance(o, int):
        return o

    if isinstance(o, str):
        return int(o.replace(" ", ""))

    return int(o)  # type: ignore


def format_freq(freq: int, **_kwargs: object) -> str:
    return f"{freq:_}".replace("_", " ")


T_contra = ty.TypeVar("T_contra", contravariant=True)


class ScanEdgesList(tk.Frame):
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

        self.columns = Row.COLUMNS
        self.colmap = {
            name: idx for idx, (name, *_) in enumerate(self.columns)
        }
        self._configure()

        self.on_record_update: (
            gui_chanlist.RecordActionCallback[Row] | None
        ) = None
        self.on_record_selected: (
            gui_chanlist.RecordSelectedCallback[Row] | None
        ) = None

    @property
    def data(self) -> ty.Iterable[model.ScanEdge]:
        for r in self.sheet.data:
            yield r.channel

    def set_data(self, data: ty.Iterable[model.ScanEdge]) -> None:
        self.sheet.set_sheet_data(list(map(Row, data)))
        self.sheet.set_all_column_widths()
        for row in range(len(self.sheet.data)):
            self.update_row_state(row)

    def selection(self) -> tuple[int, ...]:
        """Get selected rows."""
        return self.sheet.get_selected_rows(  # type: ignore
            get_cells_as_rows=True, return_tuple=True
        )

    def selection_set(self, sel: ty.Iterable[int]) -> None:
        """Set selection on `sel` rows"""
        for r in sel:
            self.sheet.select_row(r)
            self.sheet.set_xview(r)

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
                        format_function=to_int,
                        to_str_function=format_freq,
                        invalid_value="",
                    )
                ).align("right")
            elif isinstance(values, (list, tuple)):
                col.dropdown(values=values, state="").align("center")
            else:
                _LOG.error("unknown column %d: %s", idx, colname)

        self.sheet.row_index(0)
        self.sheet.hide_columns(0)

    def _on_sheet_modified(self, event: EventDataDict) -> None:
        # _LOG.debug("_on_sheet_modified: %r", event)

        data: set[Row] = set()

        for r, _c in event.cells.table:
            row = self.sheet.data[r]
            _LOG.debug("_on_sheet_modified: row=%d, data=%r", r, row)
            self.update_row_state(r)
            data.add(row)

        if data and self.on_record_update:
            self.on_record_update("update", data)

    def _on_validate_edits(self, event: EventDataDict) -> object:
        if event.eventname != "end_edit_table":
            return None

        # _LOG.debug("_on_validate_edits: %r", event)

        column = self.columns[event.column + 1]  # FIXME: visible cols
        row = self.sheet.data[event.row]
        value = event.value

        _LOG.debug(
            "_on_validate_edits: row=%d, col=%s, value=%r, row=%r",
            event.row,
            column[0],
            value,
            row,
        )

        try:
            match column[0]:
                case "start" | "end":
                    if value := int(value):
                        value = model.fix_frequency(value)

                case "name":
                    value = model.fix_name(value)

        except ValueError:
            _LOG.exception("_on_validate_edits: %r", value)
            return None

        _LOG.debug("_on_validate_edits: result value=%r", value)
        return value

    def _on_sheet_select(self, event: EventDataDict) -> None:
        # _LOG.debug("_on_sheet_select: %r", event)
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
        if event.selected.type_ == "rows":
            box = event.selected.box
            data = [self.sheet.data[r] for r in range(box.from_r, box.upto_r)]

            if data and self.on_record_update:
                self.on_record_update("delete", data)

        elif event.selected.type_ == "cells":
            r = event.selected.row
            data = [self.sheet.data[r]]

            if data and self.on_record_update:
                self.on_record_update("update", data)

    def update_row_state(self, row: int) -> None:
        """Set state of other cells in row (readony)."""
        pass

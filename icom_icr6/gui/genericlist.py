# Copyright © 2024-2025 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from collections import UserList
from itertools import cycle, starmap

from tksheet import (
    EventDataDict,
    Sheet,
    Span,
    functions,
    int_formatter,
    num2alpha,
)
from tksheet.other_classes import Box_nt

from icom_icr6 import model

_LOG = logging.getLogger(__name__)

Column = tuple[str, str, str | ty.Collection[str]]
ColumnsDef = ty.Sequence[Column]
T = ty.TypeVar("T")


@ty.runtime_checkable
class RecordActionCallback(ty.Protocol[T]):
    def __call__(self, action: str, rows: list[T]) -> None: ...


@ty.runtime_checkable
class RecordSelectedCallback(ty.Protocol[T]):
    def __call__(self, rows: list[T]) -> None: ...


def dummy_record_acton_cb(action: str, rows: list[T]) -> None:
    pass


def dummy_record_select_cb(rows: list[T]) -> None:
    pass


class Row(UserList[object], ty.Generic[T]):
    def __init__(
        self,
        data: ty.Iterable[object],
        rownnum: int = 0,
        obj: T | None = None,
    ) -> None:
        super().__init__(data)
        # position object in the list
        self.rownum: int = rownnum
        # object for row - used for validation etc
        self.obj: T | None = obj
        # map col id -> new value
        self._changes: dict[int, object] | None = None
        # map col name -> new value by map_changes func
        self.changes: dict[str, object] | None = None

    def __repr__(self) -> str:
        if self.changes:
            return f"Row<data={self.data!r}, changes={self.changes!r}>"

        return f"Row<data={self.data!r}, _changes={self._changes!r}>"

    def __setitem__(self, idx: int, val: object, /) -> None:  # type: ignore
        current_val = self.data[idx]
        if val == current_val or (val is None and current_val == ""):
            return

        if self._changes is None:
            self._changes = {idx: val}
        else:
            self._changes[idx] = val

        super().__setitem__(idx, val)

    def __hash__(self) -> int:
        return hash(f"row-{id(self.obj)}-{self.data[0]}")

    def map_changes(
        self, cols: ty.Sequence[Column], *, do_not_filter: bool = False
    ) -> ty.Self | None:
        """Fill `changes` dict using `cols` and registered in `_changes`
        values."""
        if self._changes:
            self.changes = {cols[c][0]: v for c, v in self._changes.items()}
            return self

        return self if do_not_filter else None


class GenericList2(tk.Frame, ty.Generic[T]):
    _ALTERNATE_COLOR = "#F5F5FF"
    COLUMNS: ty.ClassVar[ColumnsDef] = ()

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.sheet = Sheet(
            self,
            data=[],
            default_column_width=40,
            auto_resize_columns=30,
            alternate_color=self._ALTERNATE_COLOR,
            max_undos=0,
        )
        self.sheet.pack(expand=True, fill=tk.BOTH, side=tk.TOP)

        self.sheet.enable_bindings("all")
        self.sheet.edit_validation(self.__on_validate_edits)
        self.sheet.bind("<<SheetModified>>", self._on_sheet_modified)
        self.sheet.bind("<<SheetSelect>>", self._on_sheet_select)
        self.sheet.bind("<Delete>", self._on_delete_key)
        # disable column moving
        self.sheet.extra_bindings(
            "begin_move_columns", self._on_begin_col_move
        )
        # disable popup menu
        self.sheet.disable_bindings("right_click_popup_menu", "undo")

        # map column name to column index
        self.colmap = {
            name: idx for idx, (name, *_) in enumerate(self.COLUMNS)
        }
        self._configure_sheet()

        # function to call on data update
        self.on_record_update: RecordActionCallback[Row[T]] = (
            dummy_record_acton_cb
        )
        # function to call on select row
        self.on_record_selected: RecordSelectedCallback[Row[T]] = (
            dummy_record_select_cb
        )

    def visible_cols(self) -> list[int]:
        return self.sheet.MT.displayed_columns  # type: ignore

    # data

    def reset(self, *, scroll_top: bool = False) -> None:
        self.sheet.deselect_any(rows=None, columns=None)
        if scroll_top:
            self.sheet.see(row=0, column=0)

    @property
    def data(self) -> list[Row[T]]:
        return self.sheet.data  # type: ignore

    def set_data(self, data: ty.Iterable[T]) -> None:
        self.sheet.set_sheet_data(
            list(starmap(self._row_from_data, enumerate(data)))
        )

        for row in range(len(self.sheet.data)):
            self._update_row_state(row)

        self.sheet.set_all_column_widths()

    def update_data(self, idx: int, row: T) -> None:
        self.sheet.data[idx] = self._row_from_data(idx, row)
        self._update_row_state(idx)

    def set_data_rows(
        self, col: int, rows: ty.Iterable[tuple[int, list[object]]]
    ) -> None:
        sheet = self.sheet
        for row, data in rows:
            sheet.span((row, col), emit_event=True).data = data

    def paste(self, data: list[list[str]]) -> None:
        _LOG.debug("paste: %r", data)
        currently_selected = self.sheet.get_currently_selected()
        if not currently_selected:
            return

        box = currently_selected.box
        csel_col = currently_selected.column
        column = self.sheet.data_c(currently_selected.column)
        end_row = max(len(data) + box.from_r, box.upto_r)
        # cycle data to get required by destination number of rows
        cdata = cycle(data)

        for row in range(box.from_r, end_row):
            row_data = next(cdata)
            # validate
            ev = EventDataDict()
            ev.row = row
            res_data = []
            for col, value in enumerate(row_data, csel_col):
                ev.column = col
                ev.value = value
                try:
                    res_data.append(self._on_validate_edits(ev))
                except ValueError:
                    _LOG.exception("_on_validate_edits: %r", ev)
                    res_data.append(None)

            self.sheet.span((row, column), emit_event=True).data = res_data

    # selection

    def selection_set(self, sel: ty.Iterable[int]) -> None:
        """Set selection on `sel` rows"""
        for r in sel:
            self.sheet.select_row(r)
            self.sheet.see(row=r, column=0)

    def selected_rows(self) -> tuple[int, ...]:
        return self.sheet.get_selected_rows(  # type: ignore
            get_cells_as_rows=True, return_tuple=True
        )

    def selected_columns(self) -> list[int]:
        """get columns index include hidden ones"""
        return list(
            map(
                self.sheet.data_c,
                self.sheet.get_selected_columns(
                    get_cells_as_columns=True, return_tuple=True
                ),
            )
        )

    def selected_rows_data(self) -> list[Row[T]]:
        return [
            self.sheet.data[r]
            for r in sorted(
                self.sheet.get_selected_rows(get_cells_as_rows=True)
            )
        ]

    def selected_data(self) -> list[list[object]] | None:
        res = None

        currently_selected = self.sheet.get_currently_selected()
        if currently_selected and currently_selected.type_ == "cells":
            box = currently_selected.box
            res = self.sheet.get_data(
                box.from_r,
                self.sheet.data_c(box.from_c),
                box.upto_r,
                self.sheet.data_c(box.upto_c - 1) + 1,
            )

            # always return list of list
            if box.from_c == box.upto_c - 1:
                # one col
                if box.from_r == box.upto_r - 1:
                    # one row
                    res = [[res]]
                else:
                    res = [[c] for c in res]

            elif box.from_r == box.upto_r - 1:
                # one row
                res = [res]

        return res

    #####################

    # configuration

    def _row_from_data(self, idx: int, obj: T) -> Row[T]:
        """Map `obj` to Row object; `idx` is number of item row."""
        raise NotImplementedError

    def _configure_sheet(self) -> None:
        self.sheet.headers([c[1] for c in self.COLUMNS])

        for idx, column in enumerate(self.COLUMNS):
            span = self.sheet[num2alpha(idx)]
            self._configure_col(column, span)

        self.sheet.row_index(0)
        self.sheet.hide_columns(0)

    def _configure_col(self, column: Column, span: Span) -> None:
        colname, _c, values = column
        if values == "str":
            return

        if values == "int":
            span.format(int_formatter(invalid_value="")).align("right")

        elif values == "bool":
            # align not work on checkbox...
            span.checkbox().align("center")

        elif values == "freq":
            span.format(
                int_formatter(
                    format_function=model.fmt.parse_freq,
                    to_str_function=model.fmt.format_freq,
                    invalid_value="",
                )
            ).align("right")

        elif values == "offset":
            span.format(
                int_formatter(
                    format_function=model.fmt.parse_offset,
                    to_str_function=model.fmt.format_freq,
                    invalid_value="",
                )
            ).align("right")

        elif isinstance(values, (list, tuple)):
            span.dropdown(values=values).align("center")

        else:
            _LOG.error("unknown column: %s", colname)

    # callbacks

    def _on_sheet_modified(self, event: EventDataDict) -> None:
        # _LOG.debug("_on_sheet_modified: %r", event)

        data: list[Row[T]] = []

        if event.eventname == "move_rows":
            if not event.moved.rows:
                return

            action = "move"
            minrow = min(map(min, event.moved.rows.data.items()))
            maxrow = max(map(max, event.moved.rows.data.items()))

            for rownum in range(minrow, maxrow + 1):
                row = self.sheet.data[rownum]
                row.map_changes(self.COLUMNS)
                row.rownum = rownum
                data.append(row)

        else:
            action = "update"
            data = [
                row
                for r, _c in event.cells.table
                if (row := self.sheet.data[r].map_changes(self.COLUMNS))
            ]

        if data:
            self.on_record_update(action, data)  # pylint:disable=not-callable

    def __on_validate_edits(self, event: EventDataDict) -> object:
        _LOG.debug("__on_validate_edits: %r", event)

        if event.eventname not in ("end_edit_table", "edit_table"):
            return None

        try:
            return self._on_validate_edits(event)
        except ValueError:
            _LOG.exception("_on_validate_edits: %r", event)
            return None

    def _on_validate_edits(self, event: EventDataDict) -> object:
        """Validate object, return valid (corrected) value."""
        return event.value

    def _on_sheet_select(self, event: EventDataDict) -> None:
        # _LOG.debug("_on_sheet_select: %r", event)
        if not event.selected:
            return

        sel_box = event.selected.box

        rows = [
            self.sheet.data[r] for r in range(sel_box.from_r, sel_box.upto_r)
        ]

        self.on_record_selected(rows)  # pylint:disable=not-callable

    def _on_delete_key(self, event: tk.Event) -> None:  # type: ignore
        _LOG.debug("_on_delete_key: event=%r", event)
        selected = self.sheet.get_currently_selected()
        if not selected:
            return

        if selected.type_ == "rows":
            box = selected.box
            action = "delete"
            # there may be no other changes
            data = [self.sheet.data[r] for r in range(box.from_r, box.upto_r)]

        elif selected.type_ == "cells":
            box = self._adjust_box(selected.box)
            self.sheet[box].clear()
            action = "update"

            # only rows with changed data
            data = [
                row
                for r in range(box.from_r, box.upto_r)
                if (row := self.sheet.data[r].map_changes(self.COLUMNS))
            ]

        else:
            return

        if data:
            self.on_record_update(action, data)  # pylint:disable=not-callable

    def _update_row_state(self, row: int) -> None:
        """Set state of other cells in row (readony)."""

    def _set_cell_ro(self, row: int, colname: str, readonly: object) -> None:
        col = self.colmap.get(colname)
        if not col:
            return

        ro = bool(readonly)

        self.sheet.highlight_cells(
            row,
            column=col,
            fg="#d0d0d0" if ro else "black",
            bg=self._ALTERNATE_COLOR if row & 1 else None,
        )

        functions.set_readonly(
            self.sheet.MT.cell_options, (row, col), readonly=ro
        )

    def _on_begin_col_move(self, _event: EventDataDict) -> None:
        # prevent moving columns
        raise ValueError

    # support

    def _adjust_box(self, box: Box_nt) -> Box_nt:
        """fix box to match hidden columns."""
        return Box_nt(
            box.from_r,
            self.sheet.data_c(box.from_c),
            box.upto_r,
            self.sheet.data_c(box.upto_c - 1) + 1,
        )

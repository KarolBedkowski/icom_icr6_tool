# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from collections import UserList
from itertools import starmap

from tksheet import (
    EventDataDict,
    Sheet,
    Span,
    functions,
    int_formatter,
    num2alpha,
)

_LOG = logging.getLogger(__name__)

Column = tuple[str, str, str | ty.Collection[str]]


class BaseRow(UserList[object]):
    COLUMNS: ty.ClassVar[ty.Sequence[Column]] = ()

    def __init__(self, rownum: int, data: ty.Iterable[object]) -> None:
        super().__init__(data)
        self.rownum = rownum

    def _extracts_cols(self, data: dict[str, object]) -> list[object]:
        return [data[col] for col, *_ in self.COLUMNS]

    def __hash__(self) -> int:
        return hash(
            self.__class__.__name__ + str(self.data[0] if self.data else None)
        )


T_contra = ty.TypeVar("T_contra", contravariant=True)


@ty.runtime_checkable
class RecordActionCallback(ty.Protocol[T_contra]):
    def __call__(
        self,
        action: str,
        rows: ty.Collection[T_contra],
    ) -> None: ...


T = ty.TypeVar("T", bound=BaseRow)
RT = ty.TypeVar("RT")


@ty.runtime_checkable
class RecordSelectedCallback(ty.Protocol[T]):
    def __call__(
        self,
        rows: list[T],
    ) -> None: ...


def to_int(o: object, **_kwargs: object) -> int:
    if isinstance(o, int):
        return o

    if isinstance(o, str):
        return int(o.replace(" ", ""))

    return int(o)  # type: ignore


def format_freq(freq: int, **_kwargs: object) -> str:
    return f"{freq:_}".replace("_", " ")


class GenericList(tk.Frame, ty.Generic[T, RT]):
    _ROW_CLASS: type[BaseRow] = None  # type: ignore

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.sheet = Sheet(
            self, data=[], default_column_width=40, alternate_color="#E2EAF4"
        )
        self.sheet.enable_bindings("all")
        self.sheet.edit_validation(self.__on_validate_edits)
        self.sheet.bind("<<SheetModified>>", self._on_sheet_modified)
        self.sheet.pack(expand=True, fill=tk.BOTH, side=tk.TOP)
        self.sheet.bind("<<SheetSelect>>", self._on_sheet_select)
        self.sheet.extra_bindings("begin_delete", self._on_delete)
        self.sheet.extra_bindings(
            "begin_move_columns", self._on_begin_col_move
        )

        # disable popup menu
        self.sheet.disable_bindings("right_click_popup_menu")

        self.columns = self._ROW_CLASS.COLUMNS
        self.colmap = {
            name: idx for idx, (name, *_) in enumerate(self.columns)
        }
        self._configure()

        self.on_record_update: RecordActionCallback[T] | None = None
        self.on_record_selected: RecordSelectedCallback[T] | None = None

    @property
    def data(self) -> ty.Iterable[T | None]:
        for r in self.sheet.data:
            yield r

    def set_data(self, data: ty.Iterable[RT]) -> None:
        self.sheet.set_sheet_data(
            list(starmap(self._ROW_CLASS, enumerate(data)))
        )
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

        for idx, column in enumerate(self.columns):
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
            span.checkbox().align("center")

        elif values == "freq":
            span.format(
                int_formatter(
                    format_function=to_int,
                    to_str_function=format_freq,
                    invalid_value="",
                )
            ).align("right")

        elif isinstance(values, (list, tuple)):
            span.dropdown(values=values, state="").align("center")

        else:
            _LOG.error("unknown column: %s", colname)

    def _on_sheet_modified(self, event: EventDataDict) -> None:
        # _LOG.debug("_on_sheet_modified: %r", event)

        data: set[T] = set()

        if event.eventname == "move_rows":
            if not event.moved.rows:
                return

            minrow = min(map(min, event.moved.rows.data.items()))
            maxrow = max(map(max, event.moved.rows.data.items()))

            for rownum in range(minrow, maxrow + 1):
                row = self.sheet.data[rownum]
                row.rownum = rownum
                self.update_row_state(rownum)
                data.add(row)

            if data and self.on_record_update:
                self.on_record_update("move", data)

            return

        for r, _c in event.cells.table:
            row = self.sheet.data[r]
            _LOG.debug("_on_sheet_modified: row=%d, data=%r", r, row)
            self.update_row_state(r)
            data.add(row)

        if data and self.on_record_update:
            self.on_record_update("update", data)

    def __on_validate_edits(self, event: EventDataDict) -> object:
        if event.eventname != "end_edit_table":
            return None

        try:
            return self._on_validate_edits(event)
        except ValueError:
            _LOG.exception("_on_validate_edits: %r", event)
            return None

    def _on_validate_edits(self, event: EventDataDict) -> object:
        return event.value

    def _on_sheet_select(self, event: EventDataDict) -> None:
        # _LOG.debug("_on_sheet_select: %r", event)
        if not event.selected:
            return

        sel_box = event.selected.box

        if self.on_record_selected:
            rows = [
                self.sheet.data[r]
                for r in range(sel_box.from_r, sel_box.upto_r)
            ]
            self.on_record_selected(rows)

    def selected_rows(self) -> list[T]:
        return [
            self.sheet.data[r]
            for r in sorted(
                self.sheet.get_selected_rows(get_cells_as_rows=True)
            )
        ]

    def _on_delete(self, event: EventDataDict) -> None:
        if event.selected.type_ == "rows":
            box = event.selected.box
            data = [self.sheet.data[r] for r in range(box.from_r, box.upto_r)]

            if data and self.on_record_update:
                self.on_record_update("delete", data)

            for row in range(box.from_r, box.upto_r):
                self.update_row_state(row)

        elif event.selected.type_ == "cells":
            r = event.selected.row
            data = [self.sheet.data[r]]

            if data and self.on_record_update:
                self.on_record_update("update", data)

            self.update_row_state(r)

    def update_row_state(self, row: int) -> None:
        """Set state of other cells in row (readony)."""

    def _set_cell_ro(self, row: int, colname: str, readonly: object) -> None:
        col = self.colmap.get(colname)
        if not col:
            return

        ro = bool(readonly)

        self.sheet.highlight_cells(
            row, column=col, fg="#d0d0d0" if ro else "black"
        )
        functions.set_readonly(
            self.sheet.MT.cell_options, (row, col), readonly=ro
        )

    def _on_begin_col_move(self, _event: EventDataDict) -> None:
        # prevent moving columns
        raise ValueError

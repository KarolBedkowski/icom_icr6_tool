# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
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

_LOG = logging.getLogger(__name__)

Column = tuple[str, str, str | ty.Collection[str]]


class BaseRow(UserList[object]):
    COLUMNS: ty.ClassVar[ty.Sequence[Column]] = ()

    def __init__(self, rownum: int, data: ty.Iterable[object]) -> None:
        super().__init__(data)
        self.rownum = rownum
        self.updated: bool = False

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


def to_freq(o: object, **_kwargs: object) -> int:
    val = 0.0
    if isinstance(o, int):
        val = o
    elif isinstance(o, str):
        val = float(o.replace(" ", "").replace(",", "."))
    elif isinstance(o, float):
        pass
    else:
        val = float(o)  # type: ignore

    return int(val * 1_000_000 if 0 < val < 1400.0 else val)  # noqa:PLR2004


def format_freq(freq: int, **_kwargs: object) -> str:
    return f"{freq:_}".replace("_", " ")


class GenericList(tk.Frame, ty.Generic[T, RT]):
    _ROW_CLASS: type[BaseRow] = None  # type: ignore
    _ALTERNATE_COLOR = "#E5EFFA"

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.sheet = Sheet(
            self,
            data=[],
            default_column_width=40,
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

        self.columns = self._ROW_CLASS.COLUMNS
        self.colmap = {
            name: idx for idx, (name, *_) in enumerate(self.columns)
        }
        self._configure_sheet()

        self.on_record_update: RecordActionCallback[T] | None = None
        self.on_record_selected: RecordSelectedCallback[T] | None = None

    def reset(self, *, scroll_top: bool = False) -> None:
        self.sheet.deselect_any(rows=None, columns=None)
        if scroll_top:
            self.sheet.see(row=0, column=0)

    @property
    def data(self) -> ty.Iterable[T | None]:
        yield from self.sheet.data

    def set_data(self, data: ty.Iterable[RT]) -> None:
        _LOG.debug("set_data")
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
            self.sheet.see(row=r, column=0)

    def _configure_sheet(self) -> None:
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
                    format_function=to_freq,
                    to_str_function=format_freq,
                    invalid_value="",
                )
            ).align("right")

        elif isinstance(values, (list, tuple)):
            span.dropdown(values=values).align("center")

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
                self.on_record_update("move", data)  # pylint:disable=not-callable

            return

        for r, _c in event.cells.table:
            row = self.sheet.data[r]
            _LOG.debug("_on_sheet_modified: row=%d, data=%r", r, row)
            self.update_row_state(r)
            data.add(row)

        if data and self.on_record_update:
            self.on_record_update("update", data)  # pylint:disable=not-callable

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
            self.on_record_selected(rows)  # pylint:disable=not-callable

    def selected_rows(self) -> ty.Sequence[int]:
        return self.sheet.get_selected_rows(  # type: ignore
            get_cells_as_rows=True, return_tuple=True
        )

    def selected_columns(self) -> ty.Sequence[int]:
        """get columns index include hidden ones"""
        return list(
            map(
                self.sheet.data_c,
                self.sheet.get_selected_columns(
                    get_cells_as_columns=True, return_tuple=True
                ),
            )
        )

    def visible_cols(self) -> list[int]:
        return self.sheet.MT.displayed_columns  # type: ignore

    def selected_rows_data(self) -> list[T]:
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

    def paste(self, data: list[list[str]]) -> None:
        _LOG.debug("paste: %r", data)
        currently_selected = self.sheet.get_currently_selected()
        if not currently_selected:
            return

        box = currently_selected.box
        csel_col = currently_selected.column
        column = self.sheet.data_c(currently_selected.column)
        end_row = max(len(data) + box.from_r, box.upto_r)
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

    def set_data_rows(
        self, col: int, rows: ty.Iterable[tuple[int, list[object]]]
    ) -> None:
        sheet = self.sheet
        for row, data in rows:
            sheet.span((row, col), emit_event=True).data = data

    def _on_delete_key(self, event: tk.Event) -> None:  # type: ignore
        _LOG.debug("_on_delete_key: event=%r", event)
        selected = self.sheet.get_currently_selected()
        if not selected:
            return

        if selected.type_ == "rows":
            box = selected.box
            data = [self.sheet.data[r] for r in range(box.from_r, box.upto_r)]

            if data and self.on_record_update:
                self.on_record_update("delete", data)  # pylint:disable=not-callable

            for row in range(box.from_r, box.upto_r):
                self.update_row_state(row)

        elif selected.type_ == "cells":
            box = self.adjust_box(selected.box)
            self.sheet[box].clear()

            data = [self.sheet.data[r] for r in range(box.from_r, box.upto_r)]

            if data and self.on_record_update:
                self.on_record_update("update", data)  # pylint:disable=not-callable

            for r in range(box.from_r, box.upto_r):
                self.update_row_state(r)

    def update_row_state(self, row: int) -> None:
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

    def _set_cell_error(self, row: int, colname: str, error: object) -> None:
        err = bool(error)
        if not err:
            return

        col = self.colmap.get(colname)
        if not col:
            return

        self.sheet.highlight_cells(
            row,
            column=col,
            fg="#FF0000" if err else "black",
            bg=self._ALTERNATE_COLOR if row & 1 else None,
        )

    def _on_begin_col_move(self, _event: EventDataDict) -> None:
        # prevent moving columns
        raise ValueError

    def adjust_box(self, box: Box_nt) -> Box_nt:
        """fix box to match hidden columns."""
        return Box_nt(
            box.from_r,
            self.sheet.data_c(box.from_c),
            box.upto_r,
            self.sheet.data_c(box.upto_c - 1) + 1,
        )

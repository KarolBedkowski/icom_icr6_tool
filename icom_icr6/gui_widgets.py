# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

from __future__ import annotations

import abc
import logging
import tkinter as tk
import typing as ty
from contextlib import suppress
from enum import IntEnum
from tkinter import ttk

_LOG = logging.getLogger(__name__)


def new_entry(  # noqa: PLR0913
    parent: tk.Widget,
    row: int,
    col: int,
    label: str,
    var: tk.Variable,
    validator: str | None = None,
) -> ttk.Entry:
    tk.Label(parent, text=label).grid(
        row=row, column=col, sticky=tk.N + tk.W + tk.S, padx=6, pady=6
    )
    entry = ttk.Entry(parent, textvariable=var)
    entry.grid(
        row=row,
        column=col + 1,
        sticky=tk.N + tk.W + tk.E,
        padx=6,
        pady=6,
    )
    if validator:
        entry.configure(validate="all")
        entry.configure(validatecommand=(validator, "%P"))

    return entry


def new_combo(  # noqa: PLR0913
    parent: tk.Widget,
    row: int,
    col: int,
    label: str,
    var: tk.Variable,
    values: list[str],
) -> ttk.Combobox:
    tk.Label(parent, text=label).grid(
        row=row, column=col, sticky=tk.N + tk.W, padx=6, pady=6
    )
    combo = ttk.Combobox(
        parent,
        values=values,
        exportselection=False,
        state="readonly",
        textvariable=var,
    )
    combo.grid(
        row=row, column=col + 1, sticky=tk.N + tk.W + tk.E, padx=6, pady=6
    )
    return combo


def new_checkbox(
    parent: tk.Widget, row: int, col: int, label: str, var: tk.Variable
) -> tk.Checkbutton:
    cbox = tk.Checkbutton(
        parent,
        text=label,
        variable=var,
        onvalue=1,
        offvalue=0,
    )
    cbox.grid(row=row, column=col, sticky=tk.N + tk.W + tk.S)
    return cbox


def build_list_model(
    parent: tk.Widget,
    model: TableViewModel[T],
) -> tuple[tk.Frame, TableView2[T]]:
    frame = tk.Frame(parent)
    vert_scrollbar = ttk.Scrollbar(frame, orient="vertical")
    vert_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    hor_scrollbar = ttk.Scrollbar(frame, orient="horizontal")
    hor_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

    tree = TableView2(frame, model=model)
    tree.pack(fill=tk.BOTH, expand=True)
    vert_scrollbar.config(command=tree.yview)
    hor_scrollbar.config(command=tree.xview)
    tree.configure(
        yscrollcommand=vert_scrollbar.set, xscrollcommand=hor_scrollbar.set
    )

    return frame, tree


class TableViewColumn(ty.NamedTuple):
    colid: str
    title: str
    anchor: str
    width: int


T = ty.TypeVar("T")
TableViewModelRow = list[str] | tuple[str, ...]


class UpdateCellResult(IntEnum):
    NOOP = 0
    UPDATE_ROW = 1
    UPDATE_ALL = 2


class TableViewModel(abc.ABC, ty.Generic[T]):
    def __init__(
        self, cols: ty.Iterable[TableViewColumn] | None = None
    ) -> None:
        self.columns: list[TableViewColumn] = list(cols) if cols else []
        self.data: list[T] = []

    @abc.abstractmethod
    def get_editor(
        self,
        row: int,
        column: int,
        value: str,
        parent: TableView2[T],
    ) -> tk.Widget | None: ...

    @abc.abstractmethod
    def update_cell(
        self,
        row: int,
        column: int,
        value: str | None,  # new value
    ) -> tuple[UpdateCellResult, T | None]: ...

    @abc.abstractmethod
    def data2row(self, row: T) -> TableViewModelRow: ...

    def get_cols_id(self) -> list[str]:
        return [c.colid for c in self.columns]

    def get_rows(self) -> ty.Iterable[TableViewModelRow | None]:
        for row in self.data:
            yield self.data2row(row) if row is not None else None


class TableView2(ttk.Treeview, ty.Generic[T]):
    def __init__(
        self,
        parent: tk.Widget,
        model: TableViewModel[T],
    ) -> None:
        self.model = model
        super().__init__(parent, columns=model.get_cols_id())

        self.column("#0", width=0, stretch=tk.NO)
        for col_id, title, anchor, width in self.model.columns:
            self.column(column=col_id, anchor=anchor, width=width)  # type: ignore
            self.heading(col_id, text=title, anchor=tk.CENTER)

        self._entry_popup: tk.Widget | None = None
        self.bind("<Double-1>", self._on_double_click)
        self.bind("<<TreeviewSelect>>", self._on_channel_select)

    def _on_double_click(self, event: tk.Event) -> None:  # type: ignore
        if self._entry_popup:
            try:
                self._entry_popup.on_return(None)  # type: ignore
            except Exception:
                self._entry_popup.destroy()

            self._entry_popup = None

        # what row and column was clicked on
        iid = self.identify_row(event.y)
        if not iid:
            return

        # column as '#<num>'
        column = int(self.identify_column(event.x)[1:]) - 1
        x, y, width, height = self.bbox(iid, column)  # type: ignore
        pady = height // 2
        try:
            text = self.item(iid, "values")[column]
        except IndexError:
            text = ""

        self._entry_popup = self.model.get_editor(
            self.index(iid), column, text, self
        )
        if not self._entry_popup:
            return

        self._entry_popup.place(
            x=x, y=y + pady, width=width, height=height, anchor="w"
        )

    def _on_channel_select(self, _event: tk.Event) -> None:  # type: ignore
        if self._entry_popup:
            try:
                self._entry_popup.on_return(None)  # type: ignore
            except Exception:
                self._entry_popup.destroy()

            self._entry_popup = None

    def update_cell(self, iid: str, column: int, value: str | None) -> None:
        _LOG.debug("update_cell: %r,%r = %r", iid, column, value)
        with suppress(IndexError):
            old_value = self.item(iid, "values")[column]
            if old_value == value:
                return

        match self.model.update_cell(self.index(iid), column, value):
            case None, _:
                return
            case UpdateCellResult.UPDATE_ALL, _:
                self.update_all()
            case UpdateCellResult.UPDATE_ROW, None:
                return
            case UpdateCellResult.UPDATE_ROW, newval:
                assert newval is not None
                self.item(iid, values=self.model.data2row(newval))

    def update_all(self) -> None:
        sel = self.selection()

        self.delete(*self.get_children())
        for idx, row in enumerate(self.model.get_rows()):
            data = row or [str(idx)]
            self.insert(
                parent="", index=tk.END, iid=data[0], text="", values=data
            )

        if sel:
            with suppress(tk.TclError):
                self.selection_set(sel[0])


class ComboboxPopup(ttk.Combobox):
    master: TableView2  # type: ignore

    def __init__(
        self,
        parent: TableView2,  # type: ignore
        iid: str,
        column: int,
        text: str,
        items: list[str] | tuple[str, ...],
        **kw: object,
    ) -> None:
        super().__init__(
            parent,
            values=items,
            exportselection=False,
            state="readonly",
            **kw,  # type: ignore
        )
        self.iid = iid
        self.column = column
        self.set(text)
        self.focus_force()
        self.bind("<Return>", self.on_return)
        self.bind("<KP_Enter>", self.on_return)
        self.bind("<Escape>", lambda *_ignore: self.destroy())

    def on_return(self, _event: tk.Event | None) -> None:  # type: ignore
        self.master.update_cell(self.iid, self.column, self.get())
        self.destroy()


class EntryPopup(ttk.Entry):
    master: TableView2  # type: ignore

    def __init__(
        self,
        parent: TableView2,  # type: ignore
        iid: str,
        column: int,
        text: str,
        **kw: object,
    ) -> None:
        super().__init__(
            parent,
            style="pad.TEntry",
            exportselection=False,
            **kw,  # type: ignore
        )
        self.iid = iid
        self.column = column
        self.insert(0, text)
        self.focus_force()
        self.selection_range(0, "end")
        self.bind("<Return>", self.on_return)
        self.bind("<KP_Enter>", self.on_return)
        self.bind("<Control-a>", self._select_all)
        self.bind("<Escape>", lambda *_ignore: self.destroy())

    def with_validator(
        self, validator: ty.Callable[[str, str], bool]
    ) -> ty.Self:
        self.configure(validate="all")
        v = self.register(validator)
        self.configure(validatecommand=(v, "%S", "%P"))
        return self

    def on_return(self, _event: tk.Event | None) -> None:  # type: ignore
        self.master.update_cell(self.iid, self.column, self.get())
        self.destroy()

    def _select_all(self, _event: tk.Event) -> str:  # type: ignore
        self.selection_range(0, "end")
        return "break"


class CheckboxPopup(ttk.Checkbutton):
    master: TableView2  # type: ignore

    def __init__(
        self,
        parent: TableView2,  # type: ignore
        iid: str,
        column: int,
        text: str,
        **kw: object,
    ) -> None:
        self._var = tk.StringVar()
        super().__init__(
            parent,
            onvalue="yes",
            offvalue="no",
            variable=self._var,
            **kw,  # type:ignore
        )
        self.iid = iid
        self.column = column
        self.focus_force()
        self._var.set(text)
        self.bind("<Return>", self.on_return)
        self.bind("<KP_Enter>", self.on_return)
        self.bind("<Escape>", lambda *_ignore: self.destroy())

    def on_return(self, _event: tk.Event | None) -> None:  # type: ignore
        self.master.update_cell(self.iid, self.column, self._var.get())
        self.destroy()


class NumEntryPopup(EntryPopup):
    master: TableView2  # type: ignore

    def __init__(  # noqa: PLR0913
        self,
        parent: TableView2,  # type: ignore
        iid: str,
        column: int,
        text: str,
        min_val: int | None = None,
        max_val: int | None = None,
        **kw: object,
    ) -> None:
        super().__init__(parent, iid, column, text, **kw)

        self._min_val = min_val
        self._max_val = max_val
        self.with_validator(self._validator)

    def _validator(self, char: str, value: str) -> bool:
        if value == "":
            return True

        if char not in "01234567890":
            return False

        try:
            numval = int(value)
        except ValueError:
            return False

        return (self._min_val is None or numval > self._min_val) and (
            self._max_val is None or numval < self._max_val
        )

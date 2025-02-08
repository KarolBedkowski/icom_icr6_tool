# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

"""
Helpers for gui widgets.
"""

from __future__ import annotations

import logging
import tkinter as tk
import typing as ty
from tkinter import ttk

_LOG = logging.getLogger(__name__)


def new_entry(  # noqa: PLR0913
    parent: tk.Widget,
    row: int,
    col: int,
    label: str,
    var: tk.Variable,
    validator: str | None = None,
    *,
    colspan: int = 1,
) -> ttk.Entry:
    ttk.Label(parent, text=label).grid(
        row=row, column=col, sticky=tk.N + tk.W + tk.S, padx=6, pady=6
    )

    entry = ttk.Entry(parent, textvariable=var)
    entry.grid(
        row=row,
        column=col + 1,
        sticky=tk.N + tk.W + tk.E,
        padx=6,
        pady=6,
        columnspan=colspan,
    )
    if validator:
        entry.configure(validate="all")
        entry.configure(validatecommand=(validator, "%P"))

    return entry


def new_entry_pack(
    parent: tk.Widget,
    label: str,
    var: tk.Variable,
    validator: str | None = None,
) -> ttk.Entry:
    frame = tk.Frame(parent)

    ttk.Label(frame, text=label).pack(side=tk.LEFT, ipadx=3)

    entry = ttk.Entry(frame, textvariable=var)
    entry.pack(side=tk.LEFT, ipadx=6)

    if validator:
        entry.configure(validate="all")
        entry.configure(validatecommand=(validator, "%P"))

    frame.pack(side=tk.LEFT, padx=6, pady=6)

    return entry


def new_combo(  # noqa: PLR0913
    parent: tk.Widget,
    row: int,
    col: int,
    label: str,
    var: tk.Variable,
    values: list[str],
    *,
    colspan: int = 1,
) -> ttk.Combobox:
    ttk.Label(parent, text=label).grid(
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
        row=row,
        column=col + 1,
        sticky=tk.N + tk.W + tk.E,
        padx=6,
        pady=6,
        columnspan=colspan,
    )

    return combo


def new_checkbox(  # noqa:PLR0913
    parent: tk.Widget,
    row: int,
    col: int,
    label: str,
    var: tk.Variable,
    *,
    colspan: int = 1,
) -> ttk.Checkbutton:
    cbox = ttk.Checkbutton(
        parent,
        text=label,
        variable=var,
        onvalue=1,
        offvalue=0,
    )
    cbox.grid(
        row=row,
        column=col,
        sticky=tk.N + tk.W + tk.S,
        padx=6,
        pady=6,
        columnspan=colspan,
    )

    return cbox


def new_checkbox_pack(
    parent: tk.Widget,
    label: str,
    var: tk.Variable,
) -> ttk.Checkbutton:
    cbox = ttk.Checkbutton(
        parent,
        text=label,
        variable=var,
        onvalue=1,
        offvalue=0,
    )
    cbox.pack(side=tk.LEFT, padx=6, pady=6)

    return cbox


def new_vertical_separator(parent: tk.Widget) -> None:
    ttk.Separator(parent, orient=tk.VERTICAL).pack(
        side=tk.LEFT, padx=12, fill=tk.Y
    )


class ComboboxPopup(ttk.Combobox):
    def __init__(
        self,
        parent: ttk.Treeview,
        cell_id: object,
        text: str,
        items: list[str] | tuple[str, ...],
        on_update: ty.Callable[[object, str], None],
        **kw: object,
    ) -> None:
        super().__init__(
            parent,
            values=items,
            exportselection=False,
            state="readonly",
            **kw,  # type: ignore
        )
        self.cell_id = cell_id
        self.on_update = on_update
        self.set(text)
        self.focus_force()
        self.bind("<Return>", self.on_return)
        self.bind("<KP_Enter>", self.on_return)
        self.bind("<Escape>", lambda *_ignore: self.destroy())

    def on_return(self, _event: tk.Event | None) -> None:  # type: ignore
        self.on_update(self.cell_id, self.get())

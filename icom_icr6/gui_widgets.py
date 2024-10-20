# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import tkinter as tk
import typing as ty
from tkinter import ttk


def new_entry(
    parent: tk.Widget,
    row: int,
    col: int,
    label: str,
    var: tk.Variable,
    validator: str | None = None,
) -> ttk.Entry:
    tk.Label(parent, text=label).grid(
        row=row, column=col, sticky=tk.N + tk.W, padx=6, pady=6
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


def new_combo(
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


def build_list(
    parent: tk.Widget, columns: ty.Iterable[tuple[str, str, str, int]]
) -> tuple[tk.Frame, ttk.Treeview]:
    frame = tk.Frame(parent)
    vert_scrollbar = ttk.Scrollbar(frame, orient="vertical")
    vert_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    hor_scrollbar = ttk.Scrollbar(frame, orient="horizontal")
    hor_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

    col_ids = [c[0] for c in columns]
    tree = ttk.Treeview(frame, columns=col_ids)
    tree.column("#0", width=0, stretch=tk.NO)
    for col_id, title, anchor, width in columns:
        tree.column(column=col_id, anchor=anchor, width=width)  # type: ignore
        tree.heading(col_id, text=title, anchor=tk.CENTER)

    tree.pack(fill=tk.BOTH, expand=True)
    vert_scrollbar.config(command=tree.yview)
    hor_scrollbar.config(command=tree.xview)
    tree.configure(
        yscrollcommand=vert_scrollbar.set, xscrollcommand=hor_scrollbar.set
    )

    return frame, tree

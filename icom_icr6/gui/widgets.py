# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

"""
Helpers for gui widgets.
"""

from __future__ import annotations

import logging
import tkinter as tk
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

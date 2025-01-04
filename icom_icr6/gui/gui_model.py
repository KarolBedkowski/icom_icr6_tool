# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
# ruff: noqa: PLR2004,PLR0911,C901,PLR0912,PLR0915

""" """

from __future__ import annotations

import logging
import tkinter as tk

CHANNEL_RANGES = [
    "0-99",
    "100-199",
    "200-299",
    "300-399",
    "400-499",
    "500-599",
    "600-699",
    "700-799",
    "800-899",
    "900-999",
    "1000-1099",
    "1100-1199",
    "1200-1299",
]

_LOG = logging.getLogger(__name__)


class ListVar(tk.StringVar):
    def __init__(self, values: list[str]) -> None:
        super().__init__()
        self._values = values

    def set_raw(self, value: int | None) -> None:
        if value is not None:
            self.set(self._values[value])
        else:
            self.set("")

    def get_raw(self) -> int:
        return self._values.index(self.get())


class BoolVar(tk.IntVar):
    def set_raw(self, value: object) -> None:
        self.set(1 if value else 0)

    def get_raw(self) -> bool:
        return self.get() == 1


class Clipboard:
    _instance: Clipboard | None

    def __init__(self) -> None:
        self._content: object | None = None
        self._tk_root: tk.Tk | None = None

    @classmethod
    def initialize(cls: type[Clipboard], tk_root: tk.Tk) -> None:
        cls._instance = Clipboard()
        cls._instance._tk_root = tk_root  # noqa: SLF001

    @classmethod
    def instance(cls: type[Clipboard]) -> Clipboard:
        if not hasattr(cls, "_instance"):
            cls._instance = Clipboard()

        assert cls._instance
        return cls._instance

    def put(self, content: object | None) -> None:
        _LOG.debug("Clipboard put: %r", content)
        if self._tk_root and isinstance(content, str):
            self._tk_root.clipboard_clear()
            self._tk_root.clipboard_append(content)
            return

        self._content = content

    def get(self) -> object:
        if self._tk_root:
            try:
                return self._tk_root.clipboard_get()
            except tk.TclError:
                pass

        return self._content

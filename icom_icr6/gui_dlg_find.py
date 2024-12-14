# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from tkinter import ttk

from . import model
from .radio_memory import RadioMemory

_LOG = logging.getLogger(__name__)


@ty.runtime_checkable
class ResultSelectCallback(ty.Protocol):
    def __call__(self, kind: str, index: int) -> None: ...


class FindDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        radio_memory: RadioMemory,
        on_select_result: ResultSelectCallback,
    ) -> None:
        super().__init__(parent)  # ,  "Clone to radio")

        self._radio_memory = radio_memory
        self._query = tk.StringVar()
        self._result: list[tuple[str, object]] = []
        self._on_select_result = on_select_result

        frame_body = tk.Frame(self)
        self._body(frame_body)
        frame_body.pack(side=tk.TOP, fill=tk.BOTH, padx=12, pady=12)

        self._result_lb = tk.Listbox(
            self, selectmode=tk.SINGLE, width=100, height=20
        )
        self._result_lb.pack(
            side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=12
        )
        self._result_lb.bind("<<ListboxSelect>>", self._on_select_result_list)

        self.bind("<Escape>", self._on_close)

    def _body(self, master: tk.Widget) -> None:
        ttk.Entry(master, textvariable=self._query).pack(
            side=tk.LEFT, fill=tk.X, padx=6, pady=6, expand=True
        )

        tk.Button(
            master,
            text="Find",
            width=10,
            command=self._on_search,
            default=tk.ACTIVE,
        ).pack(side=tk.RIGHT, padx=6, pady=6)

        self.bind("<Return>", self._on_search)

    def _on_search(self, _event: tk.Event | None = None) -> None:  # type:ignore
        query = self._query.get()
        if not query:
            return

        listbox = self._result_lb
        listbox.delete(0, listbox.size())

        self._result = list(self._radio_memory.find(query))

        for kind, obj in self._result:
            if kind == "channel":
                assert isinstance(obj, model.Channel)
                line = f"Channel {obj.number}  frequency: {obj.freq} "
                if obj.name:
                    line += f" name: {obj.name}"
            else:
                line = str(obj)

            listbox.insert(tk.END, line)

    def _on_close(self, _event: tk.Event | None = None) -> None:  # type:ignore
        self.grab_release()
        self.destroy()

    def _on_select_result_list(self, _event: tk.Event) -> None:  # type: ignore
        selection = self._result_lb.curselection()  # type: ignore
        if not selection:
            return

        kind, obj = self._result[int(selection[0])]
        match kind:
            case "channel":
                assert isinstance(obj, model.Channel)
                self._on_select_result("channel", obj.number)

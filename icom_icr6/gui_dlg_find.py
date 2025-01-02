# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from tkinter import ttk

from . import config, consts, model
from .radio_memory import RadioMemory

_LOG = logging.getLogger(__name__)


@ty.runtime_checkable
class ResultSelectCallback(ty.Protocol):
    def __call__(self, kind: str, index: object) -> None: ...


class FindDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        radio_memory: RadioMemory,
        on_select_result: ResultSelectCallback,
    ) -> None:
        super().__init__(parent)
        self.title("Find")

        self._radio_memory = radio_memory
        self._query = tk.StringVar()
        self._status = tk.StringVar()
        self._status.set("")
        self._on_select_result = on_select_result

        frame_body = tk.Frame(self)
        self._body(frame_body)
        frame_body.pack(side=tk.TOP, fill=tk.BOTH, padx=12, pady=12)

        frame_status = tk.Frame(self)
        tk.Label(frame_status, textvariable=self._status).pack(side=tk.LEFT)
        frame_status.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=12)

        frame_tree, self._result_tree = self._create_result_tree()
        frame_tree.pack(
            side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=0
        )
        self._result_tree.bind(
            "<<TreeviewSelect>>", self._on_select_result_tree
        )

        self.bind("<Escape>", self._on_close)
        self.bind("<Destroy>", self._on_destroy)
        self.geometry(config.CONFIG.find_window_geometry)

    def _body(self, master: tk.Widget) -> None:
        ttk.Label(master, text="Find what: ").pack(
            side=tk.LEFT, expand=False, fill=tk.Y, padx=6
        )

        ttk.Entry(master, textvariable=self._query).pack(
            side=tk.LEFT, fill=tk.X, pady=6, expand=True
        )

        tk.Button(
            master,
            text="Find",
            width=10,
            command=self._on_search,
            default=tk.ACTIVE,
        ).pack(side=tk.RIGHT, padx=6)

        self.bind("<Return>", self._on_search)

    def _create_result_tree(self) -> tuple[tk.Widget, ttk.Treeview]:
        frame = tk.Frame(self)
        tree = ttk.Treeview(
            frame,
            selectmode=tk.BROWSE,
            columns=("freq", "mode", "name"),
        )
        tree.column("freq", width=100)
        tree.heading("freq", text="Frequency")
        tree.column("mode", width=50)
        tree.heading("mode", text="Mode")
        tree.column("name", width=50)
        tree.heading("name", text="Name")
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        tree.configure(yscrollcommand=vsb.set)

        return frame, tree

    def _on_search(self, _event: tk.Event | None = None) -> None:  # type:ignore
        query = self._query.get()
        if not query:
            return

        tree = self._result_tree
        tree.delete(*tree.get_children())

        result = self._radio_memory.find(query)
        for idx, (kind, obj) in enumerate(result):  # noqa: B007
            match kind:
                case "channel":
                    assert isinstance(obj, model.Channel)
                    chan = obj
                    ciid = tree.insert(
                        "",
                        tk.END,
                        text=f"Channel {chan.number}",
                        tags=("chan", str(chan.number)),
                        values=(
                            f"{chan.freq:_}".replace("_", " "),
                            consts.MODES[chan.mode],
                            chan.name,
                        ),
                        open=True,
                    )

                    if chan.bank != consts.BANK_NOT_SET:
                        bank = consts.BANK_NAMES[chan.bank]
                        tree.insert(
                            ciid,
                            tk.END,
                            text=f"Bank {bank} / {chan.bank_pos}",
                            tags=("bank", str(chan.bank), str(chan.bank_pos)),
                        )

                case "awchannel":
                    assert isinstance(obj, model.Channel)
                    tree.insert(
                        "",
                        tk.END,
                        text=f"Autowrite channel {obj.number}",
                        tags=("awchan", str(obj.number)),
                        values=(
                            f"{obj.freq:_}".replace("_", " "),
                            consts.MODES[obj.mode],
                            "",
                        ),
                    )

        self._status.set(f"Found {idx} elements")

    def _on_destroy(self, event: tk.Event) -> None:  # type: ignore
        if event.widget == self:
            config.CONFIG.find_window_geometry = self.geometry()

    def _on_close(self, _event: tk.Event | None = None) -> None:  # type:ignore
        self.grab_release()
        self.destroy()

    def _on_select_result_tree(self, _event: tk.Event) -> None:  # type: ignore
        selection = self._result_tree.selection()
        if not selection:
            return

        selected = self._result_tree.item(selection[0])
        match selected["tags"]:
            case ["freq", _]:
                pass

            case ["chan", num]:
                self._on_select_result("channel", int(num))

            case ["bank", bank, bank_pos]:
                self._on_select_result("bank_pos", (int(bank), int(bank_pos)))

            case ["awchan", num]:
                self._on_select_result("awchannel", int(num))

            case _:
                _LOG.error("unknown selected item: %r", selected)

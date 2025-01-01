# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from tkinter import ttk

from . import config, consts
from .radio_memory import RadioMemory

_LOG = logging.getLogger(__name__)


@ty.runtime_checkable
class ResultSelectCallback(ty.Protocol):
    def __call__(self, kind: str, index: object) -> None: ...


_PRECISIONS = {"100kHZ": 2, "1MHz": 3, "10MHz": 4}


class DuplicatedFreqDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        radio_memory: RadioMemory,
        on_select_result: ResultSelectCallback,
    ) -> None:
        super().__init__(parent)
        self.title("Find duplicated channels")

        self._radio_memory = radio_memory
        self._precision = tk.StringVar()
        self._ignore_mode = tk.IntVar()
        self._ignore_bank = tk.IntVar()
        self._status = tk.StringVar()
        self._status.set("")
        self._result: list[tuple[str, object]] = []
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
        ttk.Label(master, text="Precision: ").pack(
            side=tk.LEFT,
            expand=False,
            fill=tk.Y,
            padx=6,
        )

        ttk.Combobox(
            master,
            textvariable=self._precision,
            exportselection=False,
            state="readonly",
            values=list(_PRECISIONS),
        ).pack(side=tk.LEFT, padx=6, expand=False)
        self._precision.set("100kHZ")

        ttk.Checkbutton(
            master,
            text="Ignore mode",
            variable=self._ignore_mode,
            onvalue=1,
            offvalue=0,
        ).pack(side=tk.LEFT, padx=6)

        ttk.Checkbutton(
            master,
            text="Ignore bank",
            variable=self._ignore_bank,
            onvalue=1,
            offvalue=0,
        ).pack(side=tk.LEFT, padx=6)

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
        tree = self._result_tree
        tree.delete(*tree.get_children())

        precision = _PRECISIONS[self._precision.get()]
        result = self._radio_memory.find_duplicated_channels_freq(
            precision,
            ignore_mode=self._ignore_mode.get() == 0,
            ignore_bank=self._ignore_bank.get() == 0,
        )

        cnt_groups, cnt_channels = 0, 0

        for freq, num, channels in result:
            cnt_groups += 1
            cnt_channels += len(channels)

            fiid = tree.insert(
                "",
                tk.END,
                text=f"{freq}: {num} channels",
                tags=("freq", str(freq)),
                open=True,
            )
            for chan in channels:
                ciid = tree.insert(
                    fiid,
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

        self._status.set(
            f"Found {cnt_channels} channels in {cnt_groups} groups"
        )

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

            case _:
                _LOG.error("unknown selected item: %r", selected)

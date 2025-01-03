# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

from __future__ import annotations

import logging
import tkinter as tk
import typing as ty
from tkinter import ttk

from . import config, consts, gui_support, model

if ty.TYPE_CHECKING:
    from .radio_memory import RadioMemory

_LOG = logging.getLogger(__name__)


@ty.runtime_checkable
class ResultSelectCallback(ty.Protocol):
    def __call__(self, kind: str, index: object) -> None: ...


class _BasePage(tk.Frame):
    def __init__(
        self, parent: FindDialog, rm: RadioMemory, status_var: tk.StringVar
    ) -> None:
        super().__init__(parent)
        self._parent = parent
        self._radio_memory = rm
        self._status = status_var

    def on_search(self, _event: tk.Event | None = None) -> None:  # type:ignore
        raise NotImplementedError

    def _clear_result_tree(self) -> None:
        tree = self._parent.result_tree
        tree.delete(*tree.get_children())

    def _insert_result_channel(self, chan: model.Channel, parent: str) -> None:
        tree = self._parent.result_tree
        ciid = tree.insert(
            parent,
            tk.END,
            text=f"Channel {chan.number}",
            tags=("chan", str(chan.number)),
            values=(
                gui_support.format_freq(chan.freq),
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


class _FindChannelsPage(_BasePage):
    def __init__(
        self, parent: FindDialog, rm: RadioMemory, status_var: tk.StringVar
    ) -> None:
        super().__init__(parent, rm, status_var)
        self._query = tk.StringVar()

        ttk.Label(self, text="Find what: ").pack(
            side=tk.LEFT, expand=False, fill=tk.Y, padx=6
        )

        ttk.Entry(self, textvariable=self._query).pack(
            side=tk.LEFT, pady=6, expand=False
        )

        ttk.Button(
            self,
            text="Find",
            width=10,
            command=self.on_search,
            default=tk.ACTIVE,
        ).pack(side=tk.RIGHT, padx=6, pady=6)

    def on_search(self, _event: tk.Event | None = None) -> None:  # type:ignore
        query = self._query.get()
        if not query:
            return

        self._clear_result_tree()

        tree = self._parent.result_tree
        result = self._radio_memory.find(query)
        idx = 0
        for idx, (kind, obj) in enumerate(result):  # noqa: B007
            match kind:
                case "channel":
                    assert isinstance(obj, model.Channel)
                    self._insert_result_channel(obj, "")

                case "awchannel":
                    assert isinstance(obj, model.Channel)
                    tree.insert(
                        "",
                        tk.END,
                        text=f"Autowrite channel {obj.number}",
                        tags=("awchan", str(obj.number)),
                        values=(
                            gui_support.format_freq(obj.freq),
                            consts.MODES[obj.mode],
                            "",
                        ),
                    )

        self._status.set(f"Found {idx} elements")


_PRECISIONS = {"100kHZ": 2, "1MHz": 3, "10MHz": 4}


class _FindDuplicatedPage(_BasePage):
    def __init__(
        self, parent: FindDialog, rm: RadioMemory, status_var: tk.StringVar
    ) -> None:
        super().__init__(parent, rm, status_var)
        self._precision = tk.StringVar()
        self._ignore_mode = tk.IntVar()
        self._ignore_bank = tk.IntVar()

        ttk.Label(self, text="Precision: ").pack(
            side=tk.LEFT,
            expand=False,
            fill=tk.Y,
            padx=6,
        )

        ttk.Combobox(
            self,
            textvariable=self._precision,
            exportselection=False,
            state="readonly",
            values=list(_PRECISIONS),
        ).pack(side=tk.LEFT, padx=6, expand=False)
        self._precision.set("100kHZ")

        ttk.Checkbutton(
            self,
            text="Ignore mode",
            variable=self._ignore_mode,
            onvalue=1,
            offvalue=0,
        ).pack(side=tk.LEFT, padx=6)

        ttk.Checkbutton(
            self,
            text="Ignore bank",
            variable=self._ignore_bank,
            onvalue=1,
            offvalue=0,
        ).pack(side=tk.LEFT, padx=6)

        ttk.Button(
            self,
            text="Find",
            width=10,
            command=self.on_search,
            default=tk.ACTIVE,
        ).pack(side=tk.RIGHT, padx=6, pady=6)

    def on_search(self, _event: tk.Event | None = None) -> None:  # type:ignore
        self._clear_result_tree()

        precision = _PRECISIONS[self._precision.get()]
        result = self._radio_memory.find_duplicated_channels_freq(
            precision,
            ignore_mode=self._ignore_mode.get() == 0,
            ignore_bank=self._ignore_bank.get() == 0,
        )

        cnt_groups, cnt_channels = 0, 0
        tree = self._parent.result_tree
        for freq, num, channels in result:
            cnt_groups += 1
            cnt_channels += len(channels)

            fiid = tree.insert(
                "",
                tk.END,
                text=f"{gui_support.format_freq(freq)}: {num} channels",
                tags=("freq", str(freq)),
                open=True,
            )
            for chan in channels:
                self._insert_result_channel(chan, fiid)

        self._status.set(
            f"Found {cnt_channels} duplicated channels in {cnt_groups} groups"
        )


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

        frame_tree, self.result_tree = self._create_result_tree()
        frame_tree.pack(
            side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=0
        )
        self.result_tree.bind(
            "<<TreeviewSelect>>", self._on_select_result_tree
        )

        self.bind("<Escape>", self._on_close)
        self.bind("<Destroy>", self._on_destroy)
        self.bind("<Return>", self._on_search)
        self.geometry(config.CONFIG.find_window_geometry)

    def _body(self, parent: tk.Widget) -> None:
        self._ntb = ttk.Notebook(parent)
        self._ntb.add(
            _FindChannelsPage(self, self._radio_memory, self._status),
            text="Channels",
        )
        self._ntb.add(
            _FindDuplicatedPage(self, self._radio_memory, self._status),
            text="Duplicated channels",
        )
        self._ntb.pack(fill="both", expand=True)

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

    def _on_destroy(self, event: tk.Event) -> None:  # type: ignore
        if event.widget == self:
            config.CONFIG.find_window_geometry = self.geometry()

    def _on_close(self, _event: tk.Event | None = None) -> None:  # type:ignore
        self.grab_release()
        self.destroy()

    def _on_select_result_tree(self, _event: tk.Event) -> None:  # type: ignore
        selection = self.result_tree.selection()
        if not selection:
            return

        selected = self.result_tree.item(selection[0])
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

    def _on_search(self, _event: tk.Event | None = None) -> None:  # type:ignore
        """Global handler for <Return> key."""
        ntb = self._ntb
        page = ntb.nametowidget(ntb.select())
        assert isinstance(page, _BasePage)
        page.on_search()

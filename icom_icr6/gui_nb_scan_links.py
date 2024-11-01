# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
from tkinter import ttk

from . import model
from .gui_widgets import (
    new_entry,
)

_LOG = logging.getLogger(__name__)


class ScanLinksPage(tk.Frame):
    def __init__(
        self, parent: tk.Widget, radio_memory: model.RadioMemory
    ) -> None:
        super().__init__(parent)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._radio_memory = radio_memory
        self._sl_name = tk.StringVar()

        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self._scan_links_list = tk.Listbox(pw, selectmode=tk.SINGLE)
        self.__update_scan_links_list()

        self._scan_links_list.bind(
            "<<ListboxSelect>>", self.__on_select_scan_link
        )
        pw.add(self._scan_links_list, weight=0)

        frame = tk.Frame(pw)
        frame.rowconfigure(0, weight=0)
        frame.rowconfigure(1, weight=1)
        frame.rowconfigure(2, weight=0)
        frame.columnconfigure(0, weight=1)

        self._create_fields(frame)
        self._create_scan_edges_list(frame)
        self._create_buttons(frame)
        pw.add(frame, weight=1)

        pw.grid(
            row=0, column=0, sticky=tk.N + tk.S + tk.E + tk.W, padx=6, pady=6
        )

    def set(self, radio_memory: model.RadioMemory) -> None:
        self._radio_memory = radio_memory
        self.__update_scan_links_list()
        self.__on_select_scan_link()

    def _create_fields(self, frame: tk.Frame) -> None:
        fields = tk.Frame(frame)
        validator = self.register(validate_name)
        self._entry_sl_name = new_entry(
            fields,
            0,
            0,
            "Scan link name: ",
            self._sl_name,
            validator=validator,
        )
        self._entry_sl_name["state"] = "disabled"
        fields.grid(row=0, column=0, sticky=tk.N + tk.E + tk.W, ipady=6)

    def _create_buttons(self, parent: tk.Frame) -> None:
        frame = tk.Frame(parent, borderwidth=6)
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)

        self._btn_deselct = ttk.Button(
            frame,
            text="Select/Deselect all",
            command=self.__on_de_select,
            state="disabled",
        )
        self._btn_deselct.grid(row=3, column=0, sticky=tk.E)
        self._btn_update = ttk.Button(
            frame,
            text="Update",
            command=self.__on_update,
            state="disabled",
        )
        self._btn_update.grid(row=3, column=2, sticky=tk.E)

        frame.grid(row=3, column=0, sticky=tk.N + tk.E + tk.W, ipady=6)

    def _create_scan_edges_list(self, parent: tk.Frame) -> None:
        slf = tk.Frame(parent, borderwidth=6)
        self._scan_links_edges = []
        for idx in range(model.NUM_SCAN_EDGES):
            var = tk.IntVar()
            cb = tk.Checkbutton(
                slf,
                text=str(idx),
                variable=var,
                onvalue=1,
                offvalue=0,
                state="disabled",
            )
            cb.grid(row=idx, column=0, sticky=tk.W)
            self._scan_links_edges.append((var, cb))

        slf.grid(row=1, column=0, sticky=tk.N + tk.E + tk.W, ipady=6)

    def __update_scan_links_list(self) -> None:
        sel_sl = self._scan_links_list.curselection()  # type: ignore

        sls = self._scan_links_list
        sls.delete(0, sls.size())
        for idx in range(10):
            sl = self._radio_memory.get_scan_link(idx)
            name = f"{idx}: {sl.name}" if sl.name else str(idx)
            sls.insert(tk.END, name)

        if sel_sl:
            self._scan_links_list.selection_set(sel_sl[0])

    def __on_select_scan_link(self, _event: tk.Event | None = None) -> None:  # type: ignore
        sel_sl = self._scan_links_list.curselection()  # type: ignore
        if not sel_sl:
            self.__disable_widgets()
            return

        sl = self._radio_memory.get_scan_link(sel_sl[0])
        self._sl_name.set(sl.name.rstrip())

        for idx, (var, cb) in enumerate(self._scan_links_edges):
            se = self._radio_memory.get_scan_edge(idx)
            if se.start:
                sename = se.name or "-"
                name = f"{idx}: {sename} {se.start} - {se.end} / {se.mode}"
            else:
                name = str(idx)

            cb["text"] = name
            cb["state"] = "normal"
            var.set(1 if sl[idx] else 0)

        self._btn_deselct["state"] = "normal"
        self._btn_update["state"] = "normal"
        self._entry_sl_name["state"] = "normal"

    def __on_update(self) -> None:
        sel_sl = self._scan_links_list.curselection()  # type: ignore
        if not sel_sl:
            self.__disable_widgets()
            return

        sl = self._radio_memory.get_scan_link(sel_sl[0])
        sl.name = self._sl_name.get()
        for idx, (var, _) in enumerate(self._scan_links_edges):
            sl[idx] = var.get()

        self._radio_memory.set_scan_link(sl)
        self.__update_scan_links_list()

    def __on_de_select(self) -> None:
        sel_sl = self._scan_links_list.curselection()  # type: ignore
        if not sel_sl:
            return

        val = 1
        if all(var.get() == 1 for var, _ in self._scan_links_edges):
            val = 0

        for var, _ in self._scan_links_edges:
            var.set(val)

    def __disable_widgets(self) -> None:
        for var, cb in self._scan_links_edges:
            cb["state"] = "disabled"
            var.set(0)

        self._btn_deselct["state"] = "disabled"
        self._btn_update["state"] = "disabled"
        self._entry_sl_name["state"] = "disabled"
        self._sl_name.set("")


def validate_name(name: str | None) -> bool:
    if not name:
        return True

    try:
        model.validate_name(name)
    except ValueError:
        return False

    return True

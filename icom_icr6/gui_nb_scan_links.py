# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
from tkinter import ttk

from . import consts, gui_model, model
from .gui_widgets import new_entry

_LOG = logging.getLogger(__name__)


class _Row:
    def __init__(self, parent: tk.Widget, idx: int) -> None:
        self.idx = idx
        self.value = tk.IntVar()
        self.cb = tk.Checkbutton(
            parent,
            text=str(idx),
            variable=self.value,
            onvalue=1,
            offvalue=0,
            state="disabled",
        )
        self.labels = []
        self.cb.grid(row=idx, column=0, sticky=tk.W)
        for i, sticky in enumerate(
            [tk.W, tk.E, tk.E, tk.E + tk.W, tk.E + tk.W, tk.E + tk.W], 1
        ):
            lvar = tk.StringVar()
            lab = tk.Label(parent, text="", textvariable=lvar)
            lab.grid(row=idx, column=i, sticky=sticky, padx=12)
            self.labels.append((lvar, lab))

    def set_labels(self, *label: str) -> None:
        for (lvar, _), lab in zip(self.labels, label, strict=True):
            lvar.set(lab)

    def clear(self) -> None:
        for lvar, _ in self.labels:
            lvar.set("")

    def set_checked(self, val: object) -> None:
        self.value.set(1 if val else 0)

    def set_state(self, state: str) -> None:
        self.cb["state"] = state
        for _, lab in self.labels:
            lab["state"] = state


class ScanLinksPage(tk.Frame):
    # TODO: scrollable list or other
    def __init__(
        self, parent: tk.Widget, radio_memory: model.RadioMemory
    ) -> None:
        super().__init__(parent)

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
        self._create_fields(frame)
        self._create_scan_edges_list(frame)
        self._create_buttons(frame)
        pw.add(frame, weight=1)

        pw.pack(expand=True, fill=tk.BOTH, side=tk.TOP, padx=12, pady=12)

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
        fields.pack(side=tk.TOP, fill=tk.X, ipady=6)

    def _create_buttons(self, parent: tk.Frame) -> None:
        frame = tk.Frame(parent, borderwidth=6)
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)

        self._btn_deselect = ttk.Button(
            frame,
            text="Select/Deselect all",
            command=self.__on_de_select,
            state="disabled",
        )
        self._btn_deselect.grid(row=3, column=0, sticky=tk.E)
        self._btn_update = ttk.Button(
            frame,
            text="Update",
            command=self.__on_update,
            state="disabled",
        )
        self._btn_update.grid(row=3, column=2, sticky=tk.E)

        frame.pack(side=tk.BOTTOM, fill=tk.X, ipady=6)

    def _create_scan_edges_list(self, parent: tk.Frame) -> None:
        slf = tk.Frame(parent)

        slf.columnconfigure(0, weight=0)

        # list of tuple - vars for checkbox and labels
        self._scan_links_edges: list[_Row] = []

        for idx in range(consts.NUM_SCAN_EDGES):
            row = _Row(slf, idx)
            self._scan_links_edges.append(row)

        slf.pack(side=tk.TOP, expand=True, fill=tk.BOTH, ipady=6)

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

        for idx, row in enumerate(self._scan_links_edges):
            se = self._radio_memory.get_scan_edge(idx)
            row.set_checked(sl[idx])
            row.set_state("normal")
            if se.start:
                row.set_labels(
                    se.name or "-",
                    gui_model.format_freq(se.start),
                    gui_model.format_freq(se.end),
                    consts.STEPS[se.tuning_step],
                    consts.MODES[se.mode],
                    "ATT" if se.attenuator else "",
                )
            else:
                row.clear()

        self._btn_deselect["state"] = "normal"
        self._btn_update["state"] = "normal"
        self._entry_sl_name["state"] = "normal"

    def __on_update(self) -> None:
        sel_sl = self._scan_links_list.curselection()  # type: ignore
        if not sel_sl:
            self.__disable_widgets()
            return

        sl = self._radio_memory.get_scan_link(sel_sl[0])
        sl.name = self._sl_name.get()
        for idx, row in enumerate(self._scan_links_edges):
            sl[idx] = row.value.get()

        self._radio_memory.set_scan_link(sl)
        self.__update_scan_links_list()

    def __on_de_select(self) -> None:
        sel_sl = self._scan_links_list.curselection()  # type: ignore
        if not sel_sl:
            return

        val = 1
        if all(row.value.get() == 1 for row in self._scan_links_edges):
            val = 0

        for row in self._scan_links_edges:
            row.set_checked(val)

    def __disable_widgets(self) -> None:
        for row in self._scan_links_edges:
            row.clear()
            row.set_checked(False)
            row.set_state("disabled")

        self._btn_deselect["state"] = "disabled"
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

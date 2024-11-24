# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from tkinter import ttk

from . import consts, expimp, gui_model, gui_scanlinkslist, model
from .gui_widgets import new_entry

_LOG = logging.getLogger(__name__)


class ScanLinksPage(tk.Frame):
    # TODO: scrollable list or other
    def __init__(
        self, parent: tk.Widget, radio_memory: model.RadioMemory
    ) -> None:
        super().__init__(parent)

        self._radio_memory = radio_memory
        self._sl_name = tk.StringVar()
        self._last_selected_sl = 0

        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self._scan_links_list = tk.Listbox(pw, selectmode=tk.SINGLE)

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

    def update_tab(self, radio_memory: model.RadioMemory) -> None:
        self._radio_memory = radio_memory

        self._scan_links_list.selection_set(self._last_selected_sl)

        self.__update_scan_links_list()
        self.__update_scan_edges()
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

        self._btn_update = ttk.Button(
            fields,
            text="Update",
            command=self.__on_update_sl,
            state="disabled",
        )
        self._btn_update.grid(row=0, column=3, sticky=tk.E)

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

        frame.pack(side=tk.BOTTOM, fill=tk.X, ipady=6)

    def _create_scan_edges_list(self, parent: tk.Frame) -> None:
        self._scan_links_edges = gui_scanlinkslist.ScanLnksList(parent)
        self._scan_links_edges.pack(
            side=tk.TOP, expand=True, fill=tk.BOTH, ipady=6
        )

        self._scan_links_edges.on_record_update = self.__on_scan_edge_updated
        self._scan_links_edges.sheet.bind(
            "<Control-c>", self.__on_scan_edge_copy
        )
        self._scan_links_edges.sheet.bind(
            "<Control-v>", self.__on_scan_edge_paste
        )

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

    def __update_scan_edges(self) -> None:
        sel_sl = self._scan_links_list.curselection()  # type: ignore
        selected_se = sel_sl[0] if sel_sl else 0

        sl = self._radio_memory.get_scan_link(selected_se)

        data: list[gui_scanlinkslist.ScanLink] = [
            gui_scanlinkslist.ScanLink(
                self._radio_memory.get_scan_edge(idx), sl[idx]
            )
            for idx in range(consts.NUM_SCAN_EDGES)
        ]

        self._scan_links_edges.set_data(data)

    def __on_select_scan_link(self, _event: tk.Event | None = None) -> None:  # type: ignore
        sel_sl = self._scan_links_list.curselection()  # type: ignore
        if not sel_sl:
            self.__disable_widgets()
            return

        self._last_selected_sl = sel_sl
        sl = self._radio_memory.get_scan_link(sel_sl[0])
        self._sl_name.set(sl.name.rstrip())

        self._scan_links_edges.set_data_links(list(sl.links()))

        self._btn_deselect["state"] = "normal"
        self._btn_update["state"] = "normal"
        self._entry_sl_name["state"] = "normal"

    def __on_update_sl(self) -> None:
        sel_sl = self._scan_links_list.curselection()  # type: ignore
        if not sel_sl:
            self.__disable_widgets()
            return

        sl = self._radio_memory.get_scan_link(sel_sl[0])
        sl.name = self._sl_name.get()
        self._radio_memory.set_scan_link(sl)

        self.__update_scan_links_list()

    def __on_de_select(self) -> None:
        sel_sl = self._scan_links_list.curselection()  # type: ignore
        if not sel_sl:
            return

        val = True
        if all(row.selected for row in self._scan_links_edges.sheet.data):
            val = False

        self._scan_links_edges.set_data_links([val] * consts.NUM_SCAN_EDGES)

    def __on_scan_edge_updated(
        self, action: str, rows: ty.Collection[gui_scanlinkslist.Row]
    ) -> None:
        match action:
            case "delete":
                pass

            case "update":
                self.__do_update_scan_edge(rows)

    def __do_update_scan_edge(
        self, rows: ty.Collection[gui_scanlinkslist.Row]
    ) -> None:
        sel_sl = self._scan_links_list.curselection()  # type: ignore
        if not sel_sl:
            return

        sl = self._radio_memory.get_scan_link(sel_sl[0])

        for rec in rows:
            _LOG.debug(
                "__do_update_scan_edge: row=%r, se=%r, selected=%r",
                rec,
                rec.se,
                rec.selected,
            )
            se = rec.se
            self._radio_memory.set_scan_edge(se)

            sl[se.idx] = rec.selected

        self._radio_memory.set_scan_link(sl)

    def __on_scan_edge_copy(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._scan_links_edges.selection()
        if not sel:
            return

        ses = (self._radio_memory.get_scan_edge(row) for row in sel)
        clip = gui_model.Clipboard.instance()
        clip.put(expimp.export_scan_edges_str(ses))

    def __on_scan_edge_paste(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._scan_links_edges.selection()
        if not sel:
            return

        clip = gui_model.Clipboard.instance()

        try:
            rows = list(expimp.import_scan_edges_str(ty.cast(str, clip.get())))
        except Exception:
            _LOG.exception("import from clipboard error")
            return

        # special case - when in clipboard is one record and selected  many-
        # duplicate
        if len(sel) > 1 and len(rows) == 1:
            row = rows[0]
            for spos in sel:
                if not self.__paste_se(row, spos):
                    break

        else:
            start_num = sel[0]
            for se_num, row in enumerate(rows, start_num):
                if not self.__paste_se(row, se_num):
                    break

                if se_num == consts.NUM_SCAN_EDGES - 1:
                    break

        self.__update_scan_edges()

    def __paste_se(self, row: dict[str, object], se_num: int) -> bool:
        if not row.get("start") or not row.get("end"):
            return True

        se = self._radio_memory.get_scan_edge(se_num).clone()
        try:
            se.from_record(row)
            se.validate()
        except ValueError:
            _LOG.exception("import from clipboard error")
            _LOG.error("se_num=%d, row=%r", se_num, row)
            return False

        se.idx = se_num
        self._radio_memory.set_scan_edge(se)
        return True

    def __disable_widgets(self) -> None:
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

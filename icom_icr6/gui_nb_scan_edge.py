# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from tkinter import messagebox

from . import consts, expimp, gui_model, gui_scanedgeslist, model

_LOG = logging.getLogger(__name__)


class ScanEdgePage(tk.Frame):
    def __init__(
        self, parent: tk.Widget, radio_memory: model.RadioMemory
    ) -> None:
        super().__init__(parent)
        self._radio_memory = radio_memory
        self._last_selected_se: list[int] = []

        self._create_list(self)

    def set(
        self, radio_memory: model.RadioMemory, *, activate: bool = False
    ) -> None:
        self._radio_memory = radio_memory

        if activate:
            self._scanedges_list.selection_set(self._last_selected_se)

        self.__update_scan_edges_list()

    def _create_list(self, frame: tk.Frame) -> None:
        self._scanedges_list = gui_scanedgeslist.ScanEdgesList(frame)
        self._scanedges_list.pack(
            expand=True, fill=tk.BOTH, side=tk.TOP, padx=12, pady=12
        )

        self._scanedges_list.on_record_update = self.__on_scan_edge_updated
        self._scanedges_list.bind("<Delete>", self.__on_channel_delete)
        self._scanedges_list.sheet.bind(
            "<Control-c>", self.__on_scan_edge_copy
        )
        self._scanedges_list.sheet.bind(
            "<Control-v>", self.__on_scan_edge_paste
        )

    # def __on_channel_select(self, _event: tk.Event) -> None:  # type: ignore
    #     sel = self._scanedges_list.selection()
    #     if not sel:
    #         return

    #     self._last_selected_se = sel[0]

    #     se_num = int(sel[0])
    #     se = self._radio_memory.get_scan_edge(se_num)
    #     _LOG.debug("scan_edge: %r", se)

    def __on_scan_edge_updated(
        self, action: str, rows: ty.Collection[gui_scanedgeslist.Row]
    ) -> None:
        match action:
            case "delete":
                pass

            case "update":
                self.__do_update_scan_edge(rows)

    def __do_update_scan_edge(
        self, rows: ty.Collection[gui_scanedgeslist.Row]
    ) -> None:
        for rec in rows:
            _LOG.debug(
                "__do_update_scan_edge: row=%r, se=%r",
                rec,
                rec.se,
            )
            se = rec.se
            self._radio_memory.set_scan_edge(se)

    def __on_channel_delete(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._scanedges_list.selection()
        if not sel:
            return

        if not messagebox.askyesno(
            "Clear scan edge",
            "Clear scan edge configuration?",
            icon=messagebox.WARNING,
        ):
            return

        for se_num in sel:
            se = self._radio_memory.get_scan_edge(se_num)
            se.delete()
            self._radio_memory.set_scan_edge(se)

        self.__update_scan_edges_list()
        self._scanedges_list.selection_set(sel)

    def __update_scan_edges_list(self) -> None:
        self._scanedges_list.set_data(
            [
                self._radio_memory.get_scan_edge(idx)
                for idx in range(consts.NUM_SCAN_EDGES)
            ]
        )

    def __on_scan_edge_copy(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._scanedges_list.selection()
        if not sel:
            return

        ses = (self._radio_memory.get_scan_edge(se_num) for se_num in sel)
        clip = gui_model.Clipboard.instance()
        clip.put(expimp.export_scan_edges_str(ses))

    def __on_scan_edge_paste(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._scanedges_list.selection()
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

        self.__update_scan_edges_list()

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

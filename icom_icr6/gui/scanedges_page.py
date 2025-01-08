# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from tkinter import messagebox

from icom_icr6 import consts, expimp, model
from icom_icr6.change_manager import ChangeManeger
from icom_icr6.radio_memory import RadioMemory

from . import gui_model, scanedges_list

_LOG = logging.getLogger(__name__)


class ScanEdgesPage(tk.Frame):
    def __init__(self, parent: tk.Widget, cm: ChangeManeger) -> None:
        super().__init__(parent)
        self._change_manager = cm
        self._last_selected_se: list[int] = []

        self._create_list(self)

    def update_tab(self) -> None:
        self._scanedges_list.selection_set(self._last_selected_se)
        self.__update_scan_edges_list()

    def reset(self) -> None:
        self._scanedges_list.selection_set(())
        self.__update_scan_edges_list()

    @property
    def _radio_memory(self) -> RadioMemory:
        return self._change_manager.rm

    def _create_list(self, frame: tk.Frame) -> None:
        self._scanedges_list = scanedges_list.ScanEdgesList(frame)
        self._scanedges_list.pack(
            expand=True, fill=tk.BOTH, side=tk.TOP, padx=12, pady=12
        )

        self._scanedges_list.on_record_selected = self.__on_se_select
        self._scanedges_list.on_record_update = self.__on_scan_edge_updated
        self._scanedges_list.bind("<Delete>", self.__on_channel_delete)
        self._scanedges_list.sheet.bind(
            "<Control-c>", self.__on_scan_edge_copy
        )
        self._scanedges_list.sheet.bind(
            "<Control-v>", self.__on_scan_edge_paste
        )

    def __on_se_select(self, rows: list[scanedges_list.Row]) -> None:
        if _LOG.isEnabledFor(logging.DEBUG):
            for rec in rows:
                _LOG.debug("se selected: %r", rec.se)

    def __on_scan_edge_updated(
        self, action: str, rows: ty.Collection[scanedges_list.Row]
    ) -> None:
        match action:
            case "delete":
                self.__do_delete_scan_edge(rows)

            case "update":
                self.__do_update_scan_edge(rows)

            case "move":
                self.__do_move_scan_edge(rows)

    def __do_delete_scan_edge(
        self, rows: ty.Collection[scanedges_list.Row]
    ) -> None:
        se: model.ScanEdge | None
        if not messagebox.askyesno(
            "Delete scan edge",
            "Delete scan edge configuration?",
            icon=messagebox.WARNING,
        ):
            return

        for rec in rows:
            _LOG.debug(
                "__do_delete_scan_edge: row=%r, chan=%r",
                rec,
                rec.se,
            )
            if se := rec.se:
                se = se.clone()
                se.delete()
                self._change_manager.set_scan_edge(se)

        self._change_manager.commit()
        self.__update_scan_edges_list()

    def __do_update_scan_edge(
        self, rows: ty.Collection[scanedges_list.Row]
    ) -> None:
        for rec in rows:
            _LOG.debug(
                "__do_update_scan_edge: row=%r, se=%r",
                rec,
                rec.se,
            )
            self._change_manager.set_scan_edge(rec.se)
            rec.updated = False

        self._change_manager.commit()

    def __do_move_scan_edge(
        self, rows: ty.Collection[scanedges_list.Row]
    ) -> None:
        changes: dict[int, int] = {}
        for rec in rows:
            se = rec.se
            _LOG.debug(
                "__do_move_scan_edge: row=%r, se=%r -> %d", rec, se, rec.rownum
            )
            changes[rec.rownum] = se.idx
            se.idx = rec.rownum
            self._change_manager.set_scan_edge(se)
            rec.updated = False

        if changes:
            self._change_manager.remap_scan_links(changes)

        self._change_manager.commit()
        self.__update_scan_edges_list()

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
            se = self._radio_memory.scan_edges[se_num].clone()
            se.delete()
            self._change_manager.set_scan_edge(se)

        self._change_manager.commit()
        self.__update_scan_edges_list()
        self._scanedges_list.selection_set(sel)

    def __update_scan_edges_list(self) -> None:
        self._scanedges_list.set_data(self._radio_memory.scan_edges)

    def __on_scan_edge_copy(self, _event: tk.Event) -> None:  # type: ignore
        selected = self._scanedges_list.sheet.get_currently_selected()
        if not selected:
            return

        res = None

        if selected.type_ == "rows":
            if rows := self._scanedges_list.selected_rows():
                mses = self._radio_memory.scan_edges
                ses = (mses[se_num] for se_num in rows)
                res = expimp.export_scan_edges_str(ses)

        elif selected.type_ == "cells" and (
            data := self._scanedges_list.selected_data()
        ):
            res = expimp.export_table_as_string(data).strip()

        if res:
            gui_model.Clipboard.instance().put(res)

    def __on_scan_edge_paste(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._scanedges_list.selection()
        if not sel:
            return

        clip = gui_model.Clipboard.instance()
        data = ty.cast(str, clip.get())
        try:
            # try import whole scan edge
            self.__on_scan_edge_paste_se(sel, data)
        except ValueError:
            # try import as plain data
            self.__on_scan_edge_paste_simple(data)
        except Exception:
            _LOG.exception("__on_channel_paste error")

    def __on_scan_edge_paste_simple(self, data: str) -> None:
        try:
            rows = expimp.import_str_as_table(data)
        except ValueError:
            raise
        except Exception:
            _LOG.exception("simple import from clipboard error")
            raise

        self._scanedges_list.paste(rows)

    def __on_scan_edge_paste_se(self, sel: tuple[int, ...], data: str) -> None:
        try:
            rows = list(expimp.import_scan_edges_str(data))
        except ValueError:
            raise
        except Exception:
            _LOG.exception("import from clipboard error")
            raise

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

        se = self._radio_memory.scan_edges[se_num].clone()
        try:
            se.from_record(row)
            se.validate()
        except ValueError:
            _LOG.exception("import from clipboard error")
            _LOG.error("se_num=%d, row=%r", se_num, row)
            return False

        se.idx = se_num
        self._change_manager.set_scan_edge(se)
        self._change_manager.commit()
        return True

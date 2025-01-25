# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from tkinter import messagebox, ttk

from icom_icr6 import config, consts, expimp, fixers, validators
from icom_icr6.change_manager import ChangeManeger
from icom_icr6.radio_memory import RadioMemory

from . import gui_model, scanlinks_list
from .widgets import new_entry

_LOG = logging.getLogger(__name__)


class ScanLinksPage(tk.Frame):
    def __init__(self, parent: tk.Widget, cm: ChangeManeger) -> None:
        super().__init__(parent)

        self._change_manager = cm
        self._sl_name = tk.StringVar()
        self._sl_name.trace("w", self._on_sl_name_changed)  # type: ignore
        self._last_selected_sl = 0
        self._in_paste = False
        self._geometry_change_binded = False

        self._pw = pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self._scan_links_list = tk.Listbox(pw, selectmode=tk.SINGLE, width=10)

        self._scan_links_list.bind(
            "<<ListboxSelect>>", self._on_select_scan_link
        )
        pw.add(self._scan_links_list, weight=0)

        frame = tk.Frame(pw)
        self._create_fields(frame)
        self._create_scan_edges_list(frame)
        self._create_buttons(frame)
        pw.add(frame, weight=1)

        pw.pack(expand=True, fill=tk.BOTH, side=tk.TOP, padx=12, pady=12)

    def update_tab(self) -> None:
        self._update_scan_links_list()
        self._update_scan_edges()
        self._scan_links_list.selection_set(self._last_selected_sl)
        self._on_select_scan_link()

        self._update_geometry()

    def reset(self) -> None:
        self._update_scan_links_list()
        self._update_scan_edges()
        self._scan_links_list.selection_set(0)
        self._on_select_scan_link()

    @property
    def _radio_memory(self) -> RadioMemory:
        return self._change_manager.rm

    def _create_fields(self, frame: tk.Frame) -> None:
        fields = tk.Frame(frame)
        validator = self.register(validate_name)
        new_entry(
            fields,
            0,
            0,
            "Scan link name: ",
            self._sl_name,
            validator=validator,
        )

        fields.pack(side=tk.TOP, fill=tk.X)

    def _create_buttons(self, parent: tk.Frame) -> None:
        frame = tk.Frame(parent)

        ttk.Button(
            frame,
            text="Select/Deselect all",
            command=self._on_de_select,
        ).pack(side=tk.LEFT)

        frame.pack(side=tk.BOTTOM, fill=tk.X)

    def _create_scan_edges_list(self, parent: tk.Frame) -> None:
        self._scan_links_edges = scanlinks_list.ScanLnksList(parent)
        self._scan_links_edges.pack(
            side=tk.TOP, expand=True, fill=tk.BOTH, pady=6
        )

        self._scan_links_edges.on_record_update = self._on_scan_edge_updated
        self._scan_links_edges.sheet.bind(
            "<Control-c>", self._on_scan_edge_copy
        )
        self._scan_links_edges.sheet.bind(
            "<Control-v>", self._on_scan_edge_paste
        )

    def _update_scan_links_list(self) -> None:
        sel_sl = self._last_selected_sl

        sls = self._scan_links_list
        sls.delete(0, sls.size())
        for idx, sl in enumerate(self._radio_memory.scan_links):
            name = f"{idx}: {sl.name}" if sl.name else str(idx)
            sls.insert(tk.END, name)

        self._scan_links_list.selection_set(sel_sl)

    def _update_scan_edges(self) -> None:
        sel_sl = self._last_selected_sl

        sl = self._radio_memory.scan_links[sel_sl]

        data: list[scanlinks_list.ScanLink] = [
            scanlinks_list.ScanLink(
                self._radio_memory.scan_edges[idx], sl[idx]
            )
            for idx in range(consts.NUM_SCAN_EDGES)
        ]

        self._scan_links_edges.set_data(data)

    def _update_geometry(self) -> None:
        pos = config.CONFIG.main_window_sl_tab_pane_pos
        if pos != self._pw.sashpos(0):
            self._pw.sashpos(0, pos)

        if not self._geometry_change_binded:
            self._geometry_change_binded = True
            self._scan_links_list.bind("<Configure>", self._store_geometry)

    def _store_geometry(self, _event: tk.Event | None = None) -> None:  # type: ignore
        if pos := self._pw.sashpos(0):
            config.CONFIG.main_window_sl_tab_pane_pos = pos

    def _on_select_scan_link(self, event: tk.Event | None = None) -> None:  # type: ignore
        sel_sl = self._scan_links_list.curselection()
        if event:
            self._scan_links_edges.reset(scroll_top=True)

        if not sel_sl:
            return

        self._last_selected_sl = sel_sl[0]
        sl = self._radio_memory.scan_links[sel_sl[0]]
        self._sl_name.set(sl.name.rstrip())

        self._scan_links_edges.set_data_links(list(sl.links()))

    def _on_sl_name_changed(self, _var: str, _idx: str, _op: str) -> None:
        sl = self._radio_memory.scan_links[self._last_selected_sl]
        name = self._sl_name.get()
        fixed_name = fixers.fix_name(name)
        if sl.name == fixed_name:
            return

        if name != fixed_name:
            self._sl_name.set(fixed_name)

        sl = sl.clone()
        sl.name = fixed_name
        self._change_manager.set_scan_link(sl)
        self._change_manager.commit()
        self._update_scan_links_list()

    def _on_de_select(self) -> None:
        sel_sl = self._last_selected_sl

        val = True
        if all(
            row.obj.selected for row in self._scan_links_edges.data if row.obj
        ):
            val = False

        self._scan_links_edges.set_data_links([val] * consts.NUM_SCAN_EDGES)

        sl = self._radio_memory.scan_links[sel_sl].clone()
        for idx in range(consts.NUM_SCAN_EDGES):
            sl[idx] = val

        self._change_manager.set_scan_link(sl)
        self._change_manager.commit()

        self._update_scan_edges()

    def _on_scan_edge_updated(
        self, action: str, rows: ty.Collection[scanlinks_list.RowType]
    ) -> None:
        match action:
            case "delete":
                self._do_delete_scan_edge(rows)

            case "update":
                self._do_update_scan_edge(rows)

            case "move":
                self._do_move_scan_edge(rows)

    def _do_delete_scan_edge(
        self, rows: ty.Collection[scanlinks_list.RowType]
    ) -> None:
        if not messagebox.askyesno(
            "Delete scan edge",
            "Delete scan edge configuration?",
            icon=messagebox.WARNING,
        ):
            return

        for row in rows:
            _LOG.debug("_do_delete_scan_edge: row=%r", row)
            if sl := row.obj:
                se = sl.scan_edge.clone()
                se.delete()
                self._change_manager.set_scan_edge(se)

        self._change_manager.commit()
        self._update_scan_edges()

    def _do_update_scan_edge(
        self, rows: ty.Collection[scanlinks_list.RowType]
    ) -> None:
        sel_sl = self._last_selected_sl
        sl = self._radio_memory.scan_links[sel_sl].clone()
        ses = []

        for row in rows:
            _LOG.debug("__do_update_scan_link: row=%r", row)
            assert row.obj
            assert row.changes

            se = row.obj.scan_edge.clone()
            se.from_record(row.changes)

            if se.hidden:
                if se.start and se.end:
                    se.unhide()
                else:
                    se.edited = True

            if not se.hidden and se.start > se.end:
                se.start, se.end = se.end, se.start

            ses.append(se)

            if (sel := row.changes.get("selected")) is not None:
                sl[se.idx] = sel

        for se in ses:
            self._change_manager.set_scan_edge(se)

        self._change_manager.set_scan_link(sl)

        if not self._in_paste:
            # when in paste, commit and refresh view is at the end
            self._change_manager.commit()

            for se in ses:
                self._scan_links_edges.update_data(
                    se.idx, scanlinks_list.ScanLink(se, sl[se.idx])
                )

    def _do_move_scan_edge(
        self, rows: ty.Collection[scanlinks_list.RowType]
    ) -> None:
        changes: dict[int, int] = {}
        for row in rows:
            sl = row.obj
            assert sl
            se = sl.scan_edge
            _LOG.debug(
                "_do_move_scan_edge: row=%r, se=%r -> %d", row, se, row.rownum
            )
            changes[row.rownum] = se.idx
            se.idx = row.rownum
            self._change_manager.set_scan_edge(se)

        if changes:
            self._change_manager.remap_scan_links(changes)

        self._change_manager.commit()
        self._update_scan_edges()

    def _on_scan_edge_copy(self, _event: tk.Event) -> None:  # type: ignore
        selected = self._scan_links_edges.sheet.get_currently_selected()
        if not selected:
            return

        res = None

        if selected.type_ == "rows":
            if rows := self._scan_links_edges.selected_rows():
                mses = self._radio_memory.scan_edges
                ses = (mses[se_num] for se_num in rows)
                res = expimp.export_scan_edges_str(ses)

        elif selected.type_ == "cells" and (
            data := self._scan_links_edges.selected_data()
        ):
            res = expimp.export_table_as_string(data).strip()

        if res:
            gui_model.Clipboard.instance().put(res)

    def _on_scan_edge_paste(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._scan_links_edges.selected_rows()
        if not sel:
            return

        self._in_paste = True
        clip = gui_model.Clipboard.instance()
        data = ty.cast(str, clip.get())
        try:
            # try import whole scan edge
            if not self._on_scan_edge_paste_se(sel, data):
                self._on_scan_edge_paste_simple(data)

        except Exception as err:
            _LOG.exception("__on_channel_paste error")
            self._change_manager.abort()
            messagebox.showerror(
                "Paste data error", f"Clipboard content can't be pasted: {err}"
            )

        else:
            self._change_manager.commit()
            self._update_scan_edges()

        finally:
            self._in_paste = False

    def _on_scan_edge_paste_simple(self, data: str) -> None:
        if rows := expimp.import_str_as_table(data):
            self._scan_links_edges.paste(rows)

    def _on_scan_edge_paste_se(self, sel: tuple[int, ...], data: str) -> bool:
        try:
            rows = list(expimp.import_scan_edges_str(data))
        except ValueError:
            return False

        # special case - when in clipboard is one record and selected  many-
        # duplicate
        if len(sel) > 1 and len(rows) == 1:
            row = rows[0]
            for spos in sel:
                if not self._paste_se(row, spos):
                    break

        else:
            start_num = sel[0]
            for se_num, row in enumerate(rows, start_num):
                if not self._paste_se(row, se_num):
                    break

                if se_num == consts.NUM_SCAN_EDGES - 1:
                    break

        return True

    def _paste_se(self, row: dict[str, object], se_num: int) -> bool:
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
        se.unhide()
        self._change_manager.set_scan_edge(se)

        return True


def validate_name(name: str | None) -> bool:
    if not name:
        return True

    try:
        validators.validate_name(name)
    except ValueError:
        return False

    return True

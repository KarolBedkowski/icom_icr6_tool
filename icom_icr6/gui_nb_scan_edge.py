# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from tkinter import messagebox

from . import gui_model, model
from .gui_widgets import (
    ComboboxPopup,
    EntryPopup,
    NumEntryPopup,
    TableView2,
    TableViewColumn,
    TableViewModel,
    TableViewModelRow,
    UpdateCellResult,
    build_list_model,
)

_LOG = logging.getLogger(__name__)


class ScanEdgePage(tk.Frame):
    def __init__(
        self, parent: tk.Widget, radio_memory: model.RadioMemory
    ) -> None:
        super().__init__(parent)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._radio_memory = radio_memory

        self._create_list(self)

    def set(self, radio_memory: model.RadioMemory) -> None:
        self._radio_memory = radio_memory
        self.__update_scan_edges_list()

    def _create_list(self, frame: tk.Frame) -> None:
        self._tb_model = ScanEdgeListModel(self._radio_memory)
        ccframe, self._se_content = build_list_model(frame, self._tb_model)
        ccframe.grid(row=0, column=0, sticky=tk.N + tk.S + tk.E + tk.W)
        self._se_content.bind(
            "<<TreeviewSelect>>", self.__on_channel_select, add="+"
        )
        self._se_content.bind("<Delete>", self.__on_channel_delete)

    def __on_channel_select(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._se_content.selection()
        if not sel:
            return

        chan_num = int(sel[0])
        chan = self._radio_memory.get_channel(chan_num)
        _LOG.debug("chan: %r", chan)

    def __on_channel_delete(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._se_content.selection()
        if not sel:
            return

        if not messagebox.askyesno(
            "Clear scan edge",
            "Clear scan edge configuration?",
            icon=messagebox.WARNING,
        ):
            return

        se_num = int(sel[0])
        se = self._radio_memory.get_scan_edge(se_num)
        se.delete()
        self._radio_memory.set_scan_edge(se)
        self.__update_scan_edges_list()
        self._se_content.selection_set(sel)

    def __update_scan_edges_list(self) -> None:
        self._tb_model.data = [
            self._radio_memory.get_scan_edge(idx)
            for idx in range(model.NUM_SCAN_EDGES)
        ]
        self._se_content.update_all()


class ScanEdgeListModel(TableViewModel[model.ScanEdge]):
    def __init__(self, radio_memory: model.RadioMemory) -> None:
        super().__init__(self._columns())
        self._radio_memory = radio_memory

    def _columns(self) -> ty.Iterable[TableViewColumn]:
        tvc = TableViewColumn
        return (
            tvc("num", "Num", tk.E, 30),
            tvc("name", "Name", tk.W, 30),
            tvc("start", "Start", tk.E, 30),
            tvc("end", "End", tk.E, 30),
            tvc("ts", "TS", tk.CENTER, 30),
            tvc("mode", "Mode", tk.CENTER, 30),
            tvc("att", "ATT", tk.CENTER, 30),
        )

    def _data2iid(self, se: model.ScanEdge) -> str:
        return str(se.idx)

    def get_editor(
        self,
        row: int,
        column: int,
        value: str,
        parent: TableView2[model.ScanEdge],
    ) -> tk.Widget | None:
        coldef = self.columns[column]
        data_row = self.data[row]
        if not data_row:
            return None

        iid = self._data2iid(data_row)
        chan = self.data[row]
        _LOG.debug(
            "get_editor: row=%d[%r], col=%d[%s], value=%r, chan=%r",
            row,
            iid,
            column,
            coldef.colid,
            value,
            chan,
        )

        res: tk.Widget | None = None

        match coldef.colid:
            case "num":  # num
                res = None

            case "att":
                res = ComboboxPopup(
                    parent, iid, column, value, ["Off", "On", "-"]
                )

            case "mode":
                res = ComboboxPopup(parent, iid, column, value, model.MODES)

            case "ts":
                res = ComboboxPopup(parent, iid, column, value, model.STEPS)

            case "name":
                res = EntryPopup(parent, iid, column, value).with_validator(
                    gui_model.name_validator
                )

            case "start" | "end":
                res = NumEntryPopup(
                    parent,
                    iid,
                    column,
                    value,
                    max_val=model.MAX_FREQUENCY // 1000,
                )

        return res

    def update_cell(  # noqa: C901
        self,
        row: int,  # row
        column: int,
        value: str | None,  # new value
    ) -> tuple[UpdateCellResult, model.ScanEdge | None]:
        coldef = self.columns[column]
        se = self.data[row]
        _LOG.debug(
            "update scan-edge: %r col=%r value=%r", se, coldef.colid, value
        )

        res = UpdateCellResult.UPDATE_ROW
        colid = coldef.colid

        if (not se.start or not se.end) and colid not in ("start", "end"):
            # do not allow edit other fields if there is no start and end
            return UpdateCellResult.NOOP, None

        match colid:
            case "num":  # num
                return UpdateCellResult.NOOP, None

            case "start":
                freq = model.fix_frequency(int(value) * 1000) if value else 0
                if not se.start and freq:
                    se.mode = model.default_mode_for_freq(freq)

                se.start = freq

            case "end":
                se.end = model.fix_frequency(int(value) * 1000) if value else 0

            case "mode":
                se.mode = model.MODES.index(value) if value else 0

            case "name":
                se.name = model.fix_name(value or "")

            case "att":
                se.attn = value == "yes"

            case "ts":
                se.ts = model.STEPS.index(value) if value else 0

            case _:
                return UpdateCellResult.NOOP, None

        if se.start and se.end and se.start > se.end:
            se.start, se.end = se.end, se.start

        _LOG.debug("new scan-edge: %r", se)
        self._radio_memory.set_scan_edge(se)
        self.data[row] = se
        return res, se

    def data2row(self, se: model.ScanEdge) -> TableViewModelRow:
        if not se.start or not se.end:
            return (
                str(se.idx),
                se.name.rstrip(),
                str(se.start // 1000),
                str(se.end // 1000),
            )

        return (
            str(se.idx),
            se.name.rstrip(),
            str(se.start // 1000),
            str(se.end // 1000),
            model.STEPS[se.ts] if se.start and se.end else "",
            model.MODES[se.mode] if se.start and se.end else "",
            se.human_attn(),  # TODOL: fix
        )

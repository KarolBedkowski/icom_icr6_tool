# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from tkinter import messagebox

from . import consts, expimp, gui_model, model
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
        self._radio_memory = radio_memory

        self._create_list(self)

    def set(self, radio_memory: model.RadioMemory) -> None:
        self._radio_memory = radio_memory
        self.__update_scan_edges_list()

    def _create_list(self, frame: tk.Frame) -> None:
        self._tb_model = ScanEdgeListModel(self._radio_memory)
        ccframe, self._se_content = build_list_model(frame, self._tb_model)
        ccframe.pack(expand=True, fill=tk.BOTH, side=tk.TOP, padx=12, pady=12)

        self._se_content.bind(
            "<<TreeviewSelect>>", self.__on_channel_select, add="+"
        )
        self._se_content.bind("<Delete>", self.__on_channel_delete)
        self._se_content.bind("<Control-c>", self.__on_scan_edge_copy)
        self._se_content.bind("<Control-v>", self.__on_scan_edge_paste)

    def __on_channel_select(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._se_content.selection()
        if not sel:
            return

        se_num = int(sel[0])
        se = self._radio_memory.get_scan_edge(se_num)
        _LOG.debug("scan_edge: %r", se)

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
            for idx in range(consts.NUM_SCAN_EDGES)
        ]
        self._se_content.update_all()

    def __on_scan_edge_copy(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._se_content.selection()
        if not sel:
            return

        ses = (self._radio_memory.get_scan_edge(int(se_num)) for se_num in sel)
        clip = gui_model.Clipboard.get()
        clip.put("scan_edge", expimp.export_scan_edges_str(ses))

    def __on_scan_edge_paste(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._se_content.selection()
        if not sel:
            return

        clip = gui_model.Clipboard.get()
        if clip.object_type != "scan_edge":
            return

        try:
            rows = expimp.import_scan_edges_str(ty.cast(str, clip.content))
        except Exception:
            _LOG.exception("import from clipboard error")
            return

        start_num = int(sel[0])
        for se_num, row in enumerate(rows, start_num):
            if row.get("start"):
                se = self._radio_memory.get_scan_edge(se_num).clone()
                try:
                    se.from_record(row)
                    se.validate()
                except ValueError:
                    _LOG.exception("import from clipboard error")
                    _LOG.error("se_num=%d, row=%r", se_num, row)
                    return

                se.idx = se_num
                self._radio_memory.set_scan_edge(se)

            if se_num == consts.NUM_SCAN_EDGES - 1:
                break

        self.__update_scan_edges_list()


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
                res = ComboboxPopup(parent, iid, column, value, consts.MODES)

            case "ts":
                res = ComboboxPopup(parent, iid, column, value, consts.STEPS)

            case "name":
                res = EntryPopup(parent, iid, column, value).with_validator(
                    gui_model.name_validator
                )

            case "start" | "end":
                res = NumEntryPopup(
                    parent,
                    iid,
                    column,
                    value.replace(" ", ""),
                    max_val=consts.MAX_FREQUENCY // 1000,
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
                freq = (
                    model.fix_frequency(int(value.replace(" ", "")) * 1000)
                    if value
                    else 0
                )
                if not se.start and freq:
                    se.mode = model.default_mode_for_freq(freq)

                se.start = freq

            case "end":
                se.end = (
                    model.fix_frequency(int(value.replace(" ", "")) * 1000)
                    if value
                    else 0
                )

            case "mode":
                se.mode = consts.MODES.index(value) if value else 0

            case "name":
                se.name = model.fix_name(value or "")

            case "att":
                se.attenuator = value == "yes"

            case "ts":
                se.tuning_step = consts.STEPS.index(value) if value else 0

            case _:
                return UpdateCellResult.NOOP, None

        if se.start and se.end and se.start > se.end:
            se.start, se.end = se.end, se.start

        _LOG.debug("new scan-edge: %r", se)
        self._radio_memory.set_scan_edge(se)
        self.data[row] = se
        return res, se

    def data2row(self, se: model.ScanEdge | None) -> TableViewModelRow:
        if not se:
            return ("",)

        if not se.start or not se.end:
            return (
                str(se.idx),
                "",
                "",
                "",
            )

        return (
            str(se.idx),
            se.name.rstrip(),
            gui_model.format_freq(se.start // 1000),
            gui_model.format_freq(se.end // 1000),
            consts.STEPS[se.tuning_step] if se.start and se.end else "",
            consts.MODES[se.mode] if se.start and se.end else "",
            se.human_attn(),  # TODOL: fix
        )

# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import typing as ty

from tksheet import EventDataDict

from . import consts, fixers, gui_genericlist, model

_LOG = logging.getLogger(__name__)


class ScanLink(ty.NamedTuple):
    scan_edge: model.ScanEdge
    selected: bool


class Row(gui_genericlist.BaseRow):
    COLUMNS = (
        ("idx", "Num", "int"),
        ("selected", "Selected", "bool"),
        ("name", "Name", "str"),
        ("start", "Start", "freq"),
        ("end", "End", "freq"),
        ("ts", "Tuning Step", consts.STEPS),
        ("mode", "Mode", consts.MODES),
        ("att", "ATT", consts.ATTENUATOR),
    )

    def __init__(self, rownum: int, sl: ScanLink) -> None:
        self.se = sl.scan_edge
        self.selected = sl.selected
        super().__init__(rownum, self._from_scanedge(sl.scan_edge))

    def __setitem__(self, idx: int, val: object, /) -> None:  # type: ignore
        if val == self.data[idx]:
            return

        se = self.se
        col = self.COLUMNS[idx][0]
        match col:
            case "idx":
                return

            case "selected":
                self.selected = bool(val)
                self.data[1] = val
                return

            case "name":
                if val:
                    se = self._make_clone()
                    se.unhide()

            case "start":  # freq
                se = self._make_clone()
                se.start = val or 0  # type: ignore
                if se.start:
                    se.unhide()

                self.data = self._from_scanedge(se)
                return

            case "end":  # freq
                se = self._make_clone()
                se.end = val or 0  # type: ignore
                if se.end:
                    se.unhide()

                self.data = self._from_scanedge(se)
                return

        if se.hidden:
            return

        data = se.to_record()
        if data[col] == val:
            return

        se = self._make_clone()
        try:
            se.from_record({col: val})
        except Exception:
            _LOG.exception(
                "update scanedge from record error: %r=%r", col, val
            )
        else:
            super().__setitem__(idx, val)

    def _make_clone(self) -> model.ScanEdge:
        """Make copy of channel for updates."""
        if not self.updated:
            self.updated = True
            self.se = self.se.clone()

        return self.se

    def _from_scanedge(self, se: model.ScanEdge) -> list[object]:
        if se.hidden:
            return [se.idx, self.selected, "", "", "", "", "", ""]

        data = se.to_record()
        return [se.idx, self.selected, *(data[c[0]] for c in self.COLUMNS[2:])]


class ScanLnksList(gui_genericlist.GenericList[Row, ScanLink]):
    _ROW_CLASS = Row

    def set_data_links(self, links: list[bool]) -> None:
        # update "selected" column
        self.sheet["B"].options(transposed=True).data = links

    def _on_validate_edits(self, event: EventDataDict) -> object:
        # _LOG.debug("_on_validate_edits: %r", event)

        column = self.columns[self.sheet.data_c(event.column)]
        row = self.sheet.data[event.row]
        value = event.value

        _LOG.debug(
            "_on_validate_edits: row=%d, col=%s, value=%r, row=%r",
            event.row,
            column[0],
            value,
            row,
        )

        match column[0]:
            case "start" | "end":
                val = float(value)
                if val < 1_310:  # entered freq  # noqa: PLR2004
                    val *= 1_000_000

                if value := int(val):
                    value = fixers.fix_frequency(value)

            case "name":
                value = fixers.fix_name(value)

        _LOG.debug("_on_validate_edits: result value=%r", value)
        return value

    def update_row_state(self, row: int) -> None:
        """Set state of other cells in row (readony)."""
        data_row = self.sheet.data[row]
        se = data_row.se
        hidden = se.hidden

        self._set_cell_ro(row, "ts", hidden)
        self._set_cell_ro(row, "mode", hidden)
        self._set_cell_ro(row, "att", hidden)

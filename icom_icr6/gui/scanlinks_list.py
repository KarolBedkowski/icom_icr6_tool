# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import typing as ty

from tksheet import EventDataDict

from icom_icr6 import consts, fixers, model

from . import genericlist

_LOG = logging.getLogger(__name__)


class ScanLink(ty.NamedTuple):
    scan_edge: model.ScanEdge
    selected: bool


class Row(genericlist.BaseRow):
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

        col = self.COLUMNS[idx][0]
        match col:
            case "idx":
                pass

            case "selected":
                self.selected = bool(val)
                self.data[1] = val

            case "name":
                if val:
                    se = self._make_clone()
                    se.unhide()

                self._update_se(idx, col, val)

            case "start":  # freq
                self._update_start(val)

            case "end":  # freq
                self._update_end(val)

            case _:
                self._update_se(idx, col, val)

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

    def _update_start(self, value: object) -> None:
        se = self.se
        se = self._make_clone()
        se.start = value or 0  # type: ignore
        if se.start:
            se.unhide()

        if not se.end:
            se.end = se.start
        elif se.start > se.end:
            se.start, se.end = se.end, se.start

        self.data = self._from_scanedge(se)

    def _update_end(self, value: object) -> None:
        se = self._make_clone()
        se.end = value or 0  # type: ignore
        if se.end:
            se.unhide()

        if not se.start:
            se.start = se.end
        elif se.start > se.end:
            se.start, se.end = se.end, se.start

        self.data = self._from_scanedge(se)

    def _update_se(self, idx: int, col: str, value: object) -> None:
        se = self.se
        if se.hidden or se.to_record()[col] == value:
            return

        se = self._make_clone()
        try:
            se.from_record({col: value})
        except Exception:
            _LOG.exception(
                "update scanedge from record error: %r=%r", col, value
            )
        else:
            super().__setitem__(idx, value)


class ScanLnksList(genericlist.GenericList[Row, ScanLink]):
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
                val = genericlist.to_freq(value)
                value = fixers.fix_frequency(val)

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

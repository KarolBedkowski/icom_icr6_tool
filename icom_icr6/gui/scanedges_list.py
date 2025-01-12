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


class Row(genericlist.BaseRow):
    COLUMNS: ty.ClassVar[ty.Sequence[genericlist.Column]] = (
        ("idx", "Num", "int"),
        ("name", "Name", "str"),
        ("start", "Start", "freq"),
        ("end", "End", "freq"),
        ("ts", "Tuning Step", consts.STEPS),
        ("mode", "Mode", consts.MODES),
        ("att", "ATT", consts.ATTENUATOR),
    )

    def __init__(self, rownum: int, se: model.ScanEdge) -> None:
        self.se = se
        super().__init__(rownum, self._from_scanedge(se))

    def __setitem__(self, idx: int, val: object, /) -> None:  # type: ignore
        if val is None or val == self.data[idx]:
            return

        col = self.COLUMNS[idx][0]
        match col:
            case "idx":
                return

            case _:
                self._update_se(idx, col, val)

    def _make_clone(self) -> model.ScanEdge:
        """Make copy of channel for updates."""
        if not self.updated:
            self.updated = True
            self.se = self.se.clone()

        return self.se

    def _from_scanedge(self, se: model.ScanEdge) -> list[object]:
        if not se.hidden or se.edited:
            return self._extracts_cols(se.to_record())

        return [se.idx, None, None, None, None, None, None]

    def _update_se(self, idx: int, col: str, value: object) -> None:
        se = self.se
        if se.to_record()[col] == value:
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

        if se.hidden:
            if se.start and se.end:
                se.unhide()
            else:
                se.edited = True

        if se.start and se.end and se.start > se.end:
            se.start, se.end = se.end, se.start
            self.data = self._from_scanedge(se)


class ScanEdgesList(genericlist.GenericList[Row, model.ScanEdge]):
    _ROW_CLASS = Row

    def _on_validate_edits(self, event: EventDataDict) -> object:
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
                if value is None or value == "":
                    return value

                val = genericlist.to_freq(value)
                value = fixers.fix_frequency(val)

            case "name":
                value = fixers.fix_name(value)

            case "mode":
                value = value.upper()

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

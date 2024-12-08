# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging

from tksheet import EventDataDict

from . import consts, fixers, gui_genericlist, model

_LOG = logging.getLogger(__name__)


class Row(gui_genericlist.BaseRow):
    COLUMNS = (
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
        if val == self.data[idx]:
            return

        se = self.se
        col = self.COLUMNS[idx][0]
        match col:
            case "idx":
                return

            case "start":  # freq
                se = self._make_clone()
                se.start = val or 0  # type: ignore
                self.data = self._from_scanedge(se)
                return

            case "end":  # freq
                se = self._make_clone()
                se.end = val or 0  # type: ignore
                self.data = self._from_scanedge(se)
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
            return

        super().__setitem__(idx, val)

    def _make_clone(self) -> model.ScanEdge:
        """Make copy of channel for updates."""
        if not self.updated:
            self.updated = True
            self.se = self.se.clone()

        return self.se

    def _from_scanedge(self, se: model.ScanEdge) -> list[object]:
        return self._extracts_cols(se.to_record())


class ScanEdgesList(gui_genericlist.GenericList[Row, model.ScanEdge]):
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

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


RowType = genericlist.Row[model.ScanEdge]


class ScanEdgesList(genericlist.GenericList2[model.ScanEdge]):
    COLUMNS: ty.ClassVar[ty.Sequence[genericlist.Column]] = (
        ("idx", "Num", "int"),
        ("name", "Name", "str"),
        ("start", "Start", "freq"),
        ("end", "End", "freq"),
        ("ts", "Tuning Step", consts.STEPS),
        ("mode", "Mode", consts.MODES),
        ("att", "ATT", consts.ATTENUATOR),
    )

    def _row_from_data(
        self, idx: int, obj: model.ScanEdge
    ) -> genericlist.Row[model.ScanEdge]:
        if not obj.hidden or obj.edited:
            data = obj.to_record()
            cols = [data[col] for col, *_ in self.COLUMNS]

        else:
            cols = [obj.idx, None, None, None, None, None, None]

        return genericlist.Row(cols, idx, obj)

    def _on_validate_edits(self, event: EventDataDict) -> object:
        column = self.COLUMNS[self.sheet.data_c(event.column)]
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
        se = data_row.obj
        hidden = se.hidden

        self._set_cell_ro(row, "ts", hidden)
        self._set_cell_ro(row, "mode", hidden)
        self._set_cell_ro(row, "att", hidden)

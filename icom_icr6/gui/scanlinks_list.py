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


RowType = genericlist.Row[ScanLink]


class ScanLnksList(genericlist.GenericList2[ScanLink]):
    COLUMNS: ty.ClassVar[ty.Sequence[genericlist.Column]] = (
        ("idx", "Num", "int"),
        ("selected", "Selected", "bool"),
        ("name", "Name", "str"),
        ("start", "Start", "freq"),
        ("end", "End", "freq"),
        ("ts", "Tuning Step", consts.STEPS),
        ("mode", "Mode", consts.MODES),
        ("att", "ATT", consts.ATTENUATOR),
    )

    def set_data_links(self, links: list[bool]) -> None:
        # update "selected" column
        self.sheet["B"].options(transposed=True).data = links

    def _row_from_data(
        self, idx: int, obj: ScanLink
    ) -> genericlist.Row[ScanLink]:
        cols: list[object]

        se = obj.scan_edge
        if se.hidden and not se.edited:
            cols = [se.idx, obj.selected, None, None, None, None, None, None]

        else:
            data = se.to_record()
            cols = [
                se.idx,
                obj.selected,
                *(data[c[0]] for c in self.COLUMNS[2:]),
            ]

        return genericlist.Row(cols, idx, obj)

    def _on_validate_edits(self, event: EventDataDict) -> object:
        # _LOG.debug("_on_validate_edits: %r", event)

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
                val = model.fmt.parse_freq(value)
                value = fixers.fix_frequency(val)

            case "name":
                value = fixers.fix_name(value)

            case "mode":
                value = value.upper()

        _LOG.debug("_on_validate_edits: result value=%r", value)
        return value

    def _update_row_state(self, row: int) -> None:
        """Set state of other cells in row (readony)."""
        data_row = self.sheet.data[row]
        se = data_row.obj.scan_edge
        hidden = se.hidden

        self._set_cell_ro(row, "ts", hidden)
        self._set_cell_ro(row, "mode", hidden)
        self._set_cell_ro(row, "att", hidden)

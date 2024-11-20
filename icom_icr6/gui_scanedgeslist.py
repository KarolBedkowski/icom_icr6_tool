# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import typing as ty

from tksheet import EventDataDict

from . import consts, gui_genericlist, model

_LOG = logging.getLogger(__name__)
_BANKS = ["", *consts.BANK_NAMES]


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

    def __init__(self, se: model.ScanEdge) -> None:
        self.se = se
        super().__init__(self._from_scanedge(se))

    def __hash__(self) -> int:
        return hash(
            self.__class__.__name__ + str(self.data[0] if self.data else None)
        )

    def __setitem__(self, idx: int, val: object, /) -> None:  # type: ignore
        if val == self.data[idx]:
            return

        se = self.se
        col = self.COLUMNS[idx][0]
        match col:
            case "idx":
                return

            case "start":  # freq
                se.start = val or 0  # type: ignore
                self.data = self._from_scanedge(se)
                return

            case "end":  # freq
                se.end = val or 0  # type: ignore
                self.data = self._from_scanedge(se)
                return

        data = se.to_record()
        if data[col] == val:
            return

        try:
            se.from_record({col: val})
        except Exception:
            _LOG.exception(
                "update scanedge from record error: %r=%r", col, val
            )
            return

        super().__setitem__(idx, val)

    def _from_scanedge(self, se: model.ScanEdge) -> list[object]:
        data = se.to_record()
        return [data[col] for col, *_ in self.COLUMNS]


def to_int(o: object, **_kwargs: object) -> int:
    if isinstance(o, int):
        return o

    if isinstance(o, str):
        return int(o.replace(" ", ""))

    return int(o)  # type: ignore


def format_freq(freq: int, **_kwargs: object) -> str:
    return f"{freq:_}".replace("_", " ")


T_contra = ty.TypeVar("T_contra", contravariant=True)


class ScanEdgesList(gui_genericlist.GenericList[Row, model.ScanEdge]):
    _ROW_CLASS = Row

    def _on_validate_edits(self, event: EventDataDict) -> object:
        # _LOG.debug("_on_validate_edits: %r", event)

        column = self.columns[event.column + 1]  # FIXME: visible cols
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
                if value := int(value):
                    value = model.fix_frequency(value)

            case "name":
                value = model.fix_name(value)

        _LOG.debug("_on_validate_edits: result value=%r", value)
        return value

    def update_row_state(self, row: int) -> None:
        """Set state of other cells in row (readony)."""

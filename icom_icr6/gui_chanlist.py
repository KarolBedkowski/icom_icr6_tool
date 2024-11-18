# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from collections import UserList

from tksheet import (
    EventDataDict,
    Sheet,
    functions,
    int_formatter,
    num2alpha,
)

from . import consts, model

_LOG = logging.getLogger(__name__)
_BANKS = ["", *consts.BANK_NAMES]


class BaseRow(UserList[object]):
    COLUMNS: ty.ClassVar[
        ty.Sequence[tuple[str, str, str | ty.Collection[str]]]
    ] = ()


class Row(BaseRow):
    COLUMNS = (
        ("channel", "Num", "int"),
        ("freq", "Frequency", "freq"),
        ("mode", "Mode", consts.MODES),
        ("name", "Name", "str"),
        ("af", "AF", "bool"),
        ("att", "ATT", "bool"),  # 5
        ("ts", "Tuning Step", consts.STEPS),
        ("dup", "DUP", consts.DUPLEX_DIRS),
        ("offset", "Offset", "freq"),
        ("skip", "Skip", consts.SKIPS),
        ("vsc", "VSC", "bool"),  # 10
        ("tone_mode", "Tone", consts.TONE_MODES),
        ("tsql_freq", "TSQL", consts.CTCSS_TONES),
        ("dtsc", "DTSC", consts.DTCS_CODES),
        ("polarity", "Polarity", consts.POLARITY),
        ("bank", "Bank", _BANKS),  # 15
        ("bank_pos", "Bank pos", "int"),
        ("canceller", "Canceller", consts.CANCELLER),
        ("canceller freq", "Canceller freq", "int"),
    )

    def __init__(self, channel: model.Channel) -> None:
        self.channel = channel
        super().__init__(self._from_channel(channel))

    def __hash__(self) -> int:
        return hash(
            self.__class__.__name__ + str(self.data[0] if self.data else None)
        )

    def __setitem__(self, idx: int, val: object, /) -> None:  # type: ignore
        if val == self.data[idx]:
            return

        chan = self.channel
        col = self.COLUMNS[idx][0]

        if (not chan.freq or chan.hide_channel) and idx != 1:
            return

        match col:
            case "number":
                return

            case "freq":  # freq
                if val:
                    assert isinstance(val, int)

                    if not chan.freq or chan.hide_channel:
                        chan.load_defaults(val)

                chan.freq = val or 0  # type: ignore
                chan.hide_channel = not val
                self.data = self._from_channel(chan)
                return

        data = chan.to_record()
        if data[col] == val:
            return

        try:
            chan.from_record({col: val})
        except Exception:
            _LOG.exception("update chan from record error: %r=%r", col, val)
            return

        super().__setitem__(idx, val)

    def _from_channel(self, channel: model.Channel) -> list[object]:
        if channel is None:
            return [""] * 19

        if channel.hide_channel or not channel.freq:
            return [channel.number, *([""] * 18)]

        data = channel.to_record()
        return [data[col] for col, *_ in self.COLUMNS]

    def delete(self) -> None:
        self.channel.hide_channel = True
        self.channel.freq = 0
        self.channel.bank = consts.BANK_NOT_SET
        self.data = self._from_channel(self.channel)


def to_int(o: object, **_kwargs: object) -> int:
    if isinstance(o, int):
        return o

    if isinstance(o, str):
        return int(o.replace(" ", ""))

    return int(o)  # type: ignore


def format_freq(freq: int, **_kwargs: object) -> str:
    return f"{freq:_}".replace("_", " ")


T_contra = ty.TypeVar("T_contra", contravariant=True)


@ty.runtime_checkable
class RecordActionCallback(ty.Protocol[T_contra]):
    def __call__(
        self,
        action: str,
        rows: ty.Collection[T_contra],
    ) -> None: ...


@ty.runtime_checkable
class RecordSelectedCallback(ty.Protocol):
    def __call__(
        self,
        rows: list[Row],
    ) -> None: ...


@ty.runtime_checkable
class BankPosValidator(ty.Protocol):
    def __call__(
        self,
        bank: int | str,
        channum: int,
        bank_pos: int,
        *,
        try_set_free_slot: bool = False,
    ) -> int: ...


T = ty.TypeVar("T", bound=BaseRow)


class ChannelsList(tk.Frame, ty.Generic[T]):
    _ROW_CLASS: type[T] = Row  # type: ignore

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.sheet = Sheet(
            self, data=[], default_column_width=40, alternate_color="#E2EAF4"
        )
        self.sheet.enable_bindings("all")
        self.sheet.edit_validation(self._on_validate_edits)
        self.sheet.bind("<<SheetModified>>", self._on_sheet_modified)
        self.sheet.pack(expand=True, fill=tk.BOTH, side=tk.TOP)
        self.sheet.bind("<<SheetSelect>>", self._on_sheet_select)
        self.sheet.extra_bindings("begin_delete", self._on_delete)

        self.columns = self._ROW_CLASS.COLUMNS
        self.colmap = {
            name: idx for idx, (name, *_) in enumerate(self.columns)
        }
        self._configure()

        self.on_record_update: RecordActionCallback[T] | None = None
        self.on_record_selected: RecordSelectedCallback | None = None
        self.on_channel_bank_validate: BankPosValidator | None = None

    @property
    def data(self) -> ty.Iterable[model.Channel | None]:
        for r in self.sheet.data:
            yield r.channel

    def set_hide_canceller(self, *, hide: bool) -> None:
        canc_columns = [
            self.colmap[c] - 1 for c in ("canceller", "canceller freq")
        ]
        if hide:
            self.sheet.hide_columns(canc_columns)
        else:
            self.sheet.show_columns(canc_columns)

    def set_data(self, data: ty.Iterable[model.Channel]) -> None:
        self.sheet.set_sheet_data(list(map(Row, data)))
        self.sheet.set_all_column_widths()
        for row in range(len(self.sheet.data)):
            self.update_row_state(row)

    def selection(self) -> set[int]:
        """Get selected rows."""
        return self.sheet.get_selected_rows(get_cells_as_rows=True)  # type: ignore

    def selection_set(self, sel: ty.Iterable[int]) -> None:
        """Set selection on `sel` rows"""
        for r in sel:
            self.sheet.select_row(r)
            self.sheet.set_xview(r)

    # def _col(self, column: str) -> Span:
    #     return self.sheet[num2alpha(self.colmap[column])]

    # def _setup_dropbox(self, column: str, values: list[str]) -> None:
    #     col = self.colmap[column]
    #     self.sheet[num2alpha(col)].dropdown(
    #         values=values,
    #         state="",
    #     ).align("center")

    # def _setup_dropbox_bank(self, column: str) -> None:
    #     col = self.colmap[column]
    #     values: list[str] = ["", *consts.BANK_NAMES]
    #     self.sheet[num2alpha(col)].dropdown(
    #         values=values,
    #         state="",
    #     ).align("center")

    def _configure(self) -> None:
        self.sheet.headers([c[1] for c in self.columns])

        for idx, (colname, _c, values) in enumerate(self.columns):
            col = self.sheet[num2alpha(idx)]
            if values == "str":
                continue
            if values == "int":
                col.format(int_formatter(invalid_value="")).align("right")
            elif values == "bool":
                col.checkbox().align("center")
            elif values == "freq":
                col.format(
                    int_formatter(
                        format_function=to_int,
                        to_str_function=format_freq,
                        invalid_value="",
                    )
                ).align("right")
            elif isinstance(values, (list, tuple)):
                col.dropdown(values=values, state="").align("center")
            else:
                _LOG.error("unknown column %d: %s", idx, colname)

        self.sheet.row_index(0)
        self.sheet.hide_columns(0)

    def _on_sheet_modified(self, event: EventDataDict) -> None:
        # _LOG.debug("_on_sheet_modified: %r", event)

        data: set[Row] = set()

        for r, _c in event.cells.table:
            row = self.sheet.data[r]
            _LOG.debug("_on_sheet_modified: row=%d, data=%r", r, row)
            self.update_row_state(r)
            data.add(row)

        if data and self.on_record_update:
            self.on_record_update("update", data)

    def _on_validate_edits(self, event: EventDataDict) -> object:
        if event.eventname != "end_edit_table":
            return None

        # _LOG.debug("_on_validate_edits: %r", event)

        column = self.columns[event.column + 1]  # FIXME: visible cols
        row = self.sheet.data[event.row]
        chan = row.channel
        value = event.value

        _LOG.debug(
            "_on_validate_edits: row=%d, col=%s, value=%r, row=%r",
            event.row,
            column[0],
            value,
            row,
        )

        try:
            match column[0]:
                case "channel":
                    value = int(value)
                    if not (0 <= value <= consts.NUM_CHANNELS):
                        return None

                case "freq":
                    value = model.fix_frequency(int(value))

                case "name":
                    value = model.fix_name(value)

                case "offset":
                    if off := int(value):
                        value = max(
                            min(off, consts.MAX_OFFSET), consts.MIN_OFFSET
                        )

                case "canceller freq":
                    # round frequency to 10kHz
                    freq = (int(value) // 10) * 10
                    value = max(
                        min(freq, consts.CANCELLER_MAX_FREQ),
                        consts.CANCELLER_MIN_FREQ,
                    )
                case "bank":
                    if chan.bank != value and self.on_channel_bank_validate:
                        # change bank
                        row[16] = self.on_channel_bank_validate(
                            value,
                            chan.number,
                            0,
                            try_set_free_slot=True,
                        )

                case "bank_pos":
                    value = max(min(int(value), 99), 0)
                    if self.on_channel_bank_validate:
                        value = self.on_channel_bank_validate(
                            chan.bank, chan.number, value
                        )

        except ValueError:
            _LOG.exception("_on_validate_edits: %r", value)
            return None

        _LOG.debug("_on_validate_edits: result value=%r", value)
        return value

    def _on_sheet_select(self, event: EventDataDict) -> None:
        # _LOG.debug("_on_sheet_select: %r", event)
        if not event.selected:
            return

        if self.on_record_selected:
            sel_box = event.selected.box
            rows = [
                self.sheet.data[r]
                for r in range(sel_box.from_r, sel_box.upto_r)
            ]
            self.on_record_selected(rows)

    def selected_rows(self) -> list[T]:
        return [
            self.sheet.data[r]
            for r in self.sheet.get_selected_rows(get_cells_as_rows=True)
        ]

    def _on_delete(self, event: EventDataDict) -> None:
        if event.selected.type_ == "rows":
            box = event.selected.box
            data = []
            for r in range(box.from_r, box.upto_r):
                row = self.sheet.data[r]
                row.delete()
                data.append(row)
                self.update_row_state(r)

            if data and self.on_record_update:
                self.on_record_update("delete", data)

        elif event.selected.type_ == "cells":
            r = event.selected.row
            data = [self.sheet.data[r]]

            if data and self.on_record_update:
                self.on_record_update("update", data)

    def update_row_state(self, row: int) -> None:
        """Set state of other cells in row (readony)."""
        data_row = self.sheet.data[row]
        chan = data_row.channel

        row_is_readonly = not chan or not chan.freq or chan.hide_channel
        for c in range(2, len(self.columns)):
            functions.set_readonly(
                self.sheet.MT.cell_options, (row, c), readonly=row_is_readonly
            )

        if not chan:
            return

        self._set_cell_ro(row, "offset", not chan.duplex)
        self._set_cell_ro(row, "tsql_freq", chan.tone_mode not in (1, 2))

        dtsc = chan.tone_mode in (3, 4)
        self._set_cell_ro(row, "dtsc", not dtsc)
        self._set_cell_ro(row, "polarity", not dtsc)

        self._set_cell_ro(row, "bank_pos", chan.bank == consts.BANK_NOT_SET)
        self._set_cell_ro(row, "canceller", not chan.canceller)
        self._set_cell_ro(row, "canceller freq", not chan.duplex)

        # ts
        self.sheet.set_dropdown_values(
            row,
            self.colmap["ts"],
            values=model.tuning_steps_for_freq(chan.freq),
        )

    def _set_cell_ro(self, row: int, colname: str, readonly: object) -> None:
        col = self.colmap.get(colname)
        if not col:
            return

        ro = bool(readonly)

        self.sheet.highlight_cells(
            row, column=col, fg="#d0d0d0" if ro else "black"
        )
        functions.set_readonly(
            self.sheet.MT.cell_options, (row, col), readonly=ro
        )

# Copyright © 2024-2025 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty

from tksheet import EventDataDict, Span, functions

from icom_icr6 import consts, fixers, model, radio_memory

from . import genericlist

_LOG = logging.getLogger(__name__)
_BANKS = ["", *consts.BANK_NAMES]
_SKIPS: ty.Final = ["", "S", "P"]


RowType = genericlist.Row[model.Channel | None]
ColumnsDef = genericlist.ColumnsDef


@ty.runtime_checkable
class BankPosValidator(ty.Protocol):
    def __call__(
        self,
        bank: int | str,
        channum: int,
        bank_pos: int,
        *,
        try_set_free_slot: bool = False,
    ) -> int | None: ...


class ChannelsList2(genericlist.GenericList2[model.Channel | None]):
    COLUMNS: ty.ClassVar[genericlist.ColumnsDef] = (
        ("channel", "Num", "int"),
        ("freq", "Frequency", "freq"),
        ("mode", "Mode", consts.MODES),
        ("name", "Name", "str"),
        ("af", "AF", "bool"),
        ("att", "ATT", "bool"),  # 5
        ("ts", "Tuning Step", consts.STEPS),
        ("dup", "DUP", consts.DUPLEX_DIRS),
        ("offset", "Offset", "freq"),
        ("skip", "Skip", _SKIPS),
        ("vsc", "VSC", "bool"),  # 10
        ("tone_mode", "Tone", consts.TONE_MODES),
        ("tsql_freq", "TSQL", consts.CTCSS_TONES),
        ("dtcs", "DTCS", consts.DTCS_CODES),
        ("polarity", "Polarity", consts.POLARITY),
        ("bank", "Bank", _BANKS),  # 15
        ("bank_pos", "Bank pos", "int"),
        ("canceller", "Canceller", consts.CANCELLER),
        ("canceller freq", "Canceller freq", "int"),
    )

    _EMPTY_ROW = ("",) * 18

    def __init__(
        self, parent: tk.Widget, rm: radio_memory.RadioMemory
    ) -> None:
        super().__init__(parent)
        self._region = consts.Region.GLOBAL
        self._radio_memory = rm

        self.on_channel_bank_validate: BankPosValidator | None = None

    def _row_from_data(
        self, idx: int, obj: model.Channel | None
    ) -> genericlist.Row[model.Channel | None]:
        if obj is None:
            cols = [idx, *self._EMPTY_ROW]

        elif obj.hide_channel:
            cols = [obj.number, *self._EMPTY_ROW]

        else:
            data = obj.to_record()
            if obj.bank != consts.BANK_NOT_SET:
                data["bank"] = self._radio_memory.banks[obj.bank].full_name

            cols = [data[col] for col, *_ in self.COLUMNS]

        return genericlist.Row(cols, idx, obj)

    def set_radio_memory(self, rm: radio_memory.RadioMemory) -> None:
        self._radio_memory = rm
        self._region = rm.region

        # hide canceller if region is other than Japan
        canc_columns = [
            self.colmap[c] - 1 for c in ("canceller", "canceller freq")
        ]

        if self._region != consts.Region.JAPAN:
            self.sheet.hide_columns(canc_columns)
        else:
            self.sheet.show_columns(canc_columns)

    def _configure_col(self, column: genericlist.Column, span: Span) -> None:
        _colname, _c, values = column
        if values == "bool" or isinstance(values, (list, tuple)):
            # do not create checkbox and dropdown for columns; create
            # it for cell - bellow
            span.align("center")

        else:
            super()._configure_col(column, span)

    def _on_validate_edits(self, event: EventDataDict) -> object:  # noqa:C901
        # _LOG.debug("_on_validate_edits: %r", event)
        # WARN: validation not work on checkbox

        column_idx = self.sheet.data_c(event.column)
        column = self.COLUMNS[column_idx]
        row = self.data[event.row]
        chan = row.obj
        value = event.value

        # skip validation for not-changed cells
        if value == row[column_idx]:
            return value

        _LOG.debug(
            "_on_validate_edits: row=%d, col=%s, value=%r, row=%r",
            event.row,
            column[0],
            value,
            row,
        )

        match column[0]:
            case "channel":
                value = int(value)
                if not 0 <= value < consts.NUM_CHANNELS:
                    return None

            case "freq":
                value = fixers.fix_frequency(genericlist.to_freq(value))

            case "name":
                value = fixers.fix_name(value)

            case "mode":
                value = value.upper()

            case "offset" if chan:
                if off := genericlist.to_freq(value):
                    value = fixers.fix_offset(chan.freq, off)
                else:
                    value = 0

            case "canceller freq":
                # round frequency to 10kHz
                freq = (int(value) // 10) * 10
                value = max(
                    min(freq, consts.CANCELLER_MAX_FREQ),
                    consts.CANCELLER_MIN_FREQ,
                )

            case "bank" if chan and value:
                value = self._validate_bank(value, row)

            case "bank_pos" if chan and value:
                value = self._validate_bank_pos(value, chan)

        _LOG.debug("_on_validate_edits: result value=%r", value)
        return value

    def _validate_bank(
        self, value: str, row: genericlist.Row[model.Channel]
    ) -> object:
        value = value.strip()
        chan = row.obj
        assert chan

        if not self.on_channel_bank_validate:
            return value

        # change bank,
        bank_pos = self.on_channel_bank_validate(  # pylint:disable=not-callable
            value[0] if value else "",
            chan.number,
            0,
            try_set_free_slot=True,
        )
        if bank_pos is None:
            return None

        row[16] = bank_pos
        return self._radio_memory.get_bank_fullname(value)

    def _validate_bank_pos(self, value: object, chan: model.Channel) -> object:
        if value == "" or value is None:
            return value

        pos = max(min(int(value), 99), 0)  # type: ignore

        if self.on_channel_bank_validate:
            pos = self.on_channel_bank_validate(  # pylint:disable=not-callable
                chan.bank, chan.number, pos
            )

        return pos

    def update_row_state(self, row: int) -> None:
        """Set state of other cells in row (readony)."""
        data_row: genericlist.Row[model.Channel] = self.sheet.data[row]
        chan = data_row.obj

        row_is_readonly = not chan or not chan.freq or chan.hide_channel
        for c in range(2, len(self.COLUMNS)):
            functions.set_readonly(
                self.sheet.MT.cell_options, (row, c), readonly=row_is_readonly
            )

        if row_is_readonly:
            # remove all checkboxes, dropdown when row is empty
            for col in range(len(self.COLUMNS)):
                self.sheet.span(row, col).del_dropdown().del_checkbox()

            return

        assert chan is not None

        # create dropdown, checkboxes
        for idx, (colname, _, values) in enumerate(self.COLUMNS):
            span = self.sheet.span(row, idx)
            if values == "bool":
                span.checkbox()

            elif colname == "mode":
                # mode depend on market
                vals = (
                    consts.MODES_JAP
                    if self._region.is_japan
                    else consts.MODES_NON_JAP
                )
                span.dropdown(values=vals, set_value=data_row[idx])

            elif colname == "ts":
                # tuning step depend on frequency and market

                span.dropdown(
                    values=consts.tuning_steps_for_freq(
                        chan.freq, self._region
                    ),
                    set_value=data_row[idx],
                )

            elif colname == "bank":
                # use full bank names
                names = [bank.full_name for bank in self._radio_memory.banks]
                sel = (
                    names[chan.bank]
                    if chan.bank != consts.BANK_NOT_SET
                    else ""
                )
                span.dropdown(names, set_value=sel)
                span.align("W")

            elif isinstance(values, (list, tuple)):
                span.dropdown(values, set_value=data_row[idx])

        self._set_cell_ro(row, "offset", not chan.duplex)
        self._set_cell_ro(row, "tsql_freq", chan.tone_mode not in (1, 2))

        dtcs = chan.tone_mode in (3, 4)
        self._set_cell_ro(row, "dtcs", not dtcs)
        self._set_cell_ro(row, "polarity", not dtcs)

        self._set_cell_ro(row, "bank_pos", chan.bank == consts.BANK_NOT_SET)
        # canceller is only in Japan model and when mode is FM or Auto
        self._set_cell_ro(row, "canceller", chan.mode not in (0, 3))
        self._set_cell_ro(row, "canceller freq", chan.canceller != 1)

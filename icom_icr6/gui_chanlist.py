# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty

from tksheet import EventDataDict, Span, functions

from . import consts, fixers, gui_genericlist, model

_LOG = logging.getLogger(__name__)
_BANKS = ["", *consts.BANK_NAMES]
_SKIPS: ty.Final = ["", "S", "P"]


class Row(gui_genericlist.BaseRow):
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

    def __init__(self, rownum: int, channel: model.Channel) -> None:
        self.channel = channel
        self.new_freq = 0
        super().__init__(rownum, self._from_channel(channel))
        self.errors: tuple[str, ...] = ()

    def __repr__(self) -> str:
        return (
            f"ROW: data={self.data!r} channel={self.channel} "
            f"updated={self.updated}"
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

            case "freq":
                self._update_freq(val)
                return

        data = chan.to_record()
        current_val = data[col]
        if current_val == val or (current_val == "" and val is None):
            return

        chan = self._make_clone()

        try:
            chan.from_record({col: val})
        except Exception:
            _LOG.exception("update chan from record error: %r=%r", col, val)
            return

        super().__setitem__(idx, val)

    def _make_clone(self) -> model.Channel:
        """Make copy of channel for updates."""
        if not self.updated:
            self.updated = True
            self.channel = self.channel.clone()

        return self.channel

    def _from_channel(self, channel: model.Channel) -> list[object]:
        if channel is None:
            return [""] * 19

        if channel.hide_channel or not channel.freq:
            return [channel.number, *([""] * 18)]

        try:
            return self._extracts_cols(channel.to_record())
        except Exception:
            _LOG.exception("_extracts_cols from %r error", channel)

        return [""] * 19

    def _update_freq(self, value: object) -> None:
        try:
            freq = int(value or 0)  # type: ignore
        except (ValueError, TypeError):
            return

        chan = self.channel

        if (not chan.freq or chan.hide_channel) and freq:
            self.new_freq = freq
            return

        chan = self._make_clone()
        chan.freq = freq
        if freq:
            chan.tuning_step = fixers.fix_tuning_step(
                chan.freq, chan.tuning_step
            )

        chan.hide_channel = not freq
        self.data = self._from_channel(chan)


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


class ChannelsList(gui_genericlist.GenericList[Row, model.Channel]):
    _ROW_CLASS: type[gui_genericlist.BaseRow] = Row

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.region = consts.Region.GLOBAL

        self.on_channel_bank_validate: BankPosValidator | None = None

    def set_region(self, region: consts.Region) -> None:
        _LOG.debug("set_region: %r", region)
        self.region = region
        self.set_hide_canceller(hide=region != consts.Region.JAPAN)

    def set_hide_canceller(self, *, hide: bool) -> None:
        canc_columns = [
            self.colmap[c] - 1 for c in ("canceller", "canceller freq")
        ]

        if hide:
            self.sheet.hide_columns(canc_columns)
        else:
            self.sheet.show_columns(canc_columns)

    def _configure_col(
        self, column: gui_genericlist.Column, span: Span
    ) -> None:
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

        column = self.columns[self.sheet.data_c(event.column)]
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

        match column[0]:
            case "channel":
                value = int(value)
                if not 0 <= value <= consts.NUM_CHANNELS:
                    return None

            case "freq":
                val = gui_genericlist.to_freq(value)
                value = fixers.fix_frequency(val)

            case "name":
                value = fixers.fix_name(value)

            case "offset":
                val = gui_genericlist.to_freq(value)
                value = (
                    fixers.fix_offset(chan.freq, off) if (off := val) else 0
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
                    # change bank,
                    bank_pos = self.on_channel_bank_validate(  # pylint:disable=not-callable
                        value,
                        chan.number,
                        0,
                        try_set_free_slot=True,
                    )
                    if bank_pos is None:
                        return None

                    row[16] = bank_pos

            case "bank_pos":
                if value != "" and value is not None:
                    value = max(min(int(value), 99), 0)
                    if self.on_channel_bank_validate:
                        value = (
                            self.on_channel_bank_validate(  # pylint:disable=not-callable
                                chan.bank, chan.number, value
                            )
                            if self.on_channel_bank_validate
                            else value
                        )

        _LOG.debug("_on_validate_edits: result value=%r", value)
        return value

    def update_row_state(self, row: int) -> None:
        """Set state of other cells in row (readony)."""
        data_row = self.sheet.data[row]
        chan = data_row.channel

        row_is_readonly = not chan or not chan.freq or chan.hide_channel
        for c in range(2, len(self.columns)):
            functions.set_readonly(
                self.sheet.MT.cell_options, (row, c), readonly=row_is_readonly
            )

        if row_is_readonly:
            # remove all checkboxes, dropdown when row is empty
            for col, _ in enumerate(self.columns):
                self.sheet.span(row, col).del_dropdown().del_checkbox().clear()

            return

        # create dropdown, checkboxes
        for idx, (colname, _, values) in enumerate(self.columns):
            span = self.sheet.span(row, idx)
            if values == "bool":
                span.checkbox()

            elif colname == "mode":
                # mode depend on market
                vals = (
                    consts.MODES_JAP
                    if self.region.is_japan
                    else consts.MODES_NON_JAP
                )
                span.dropdown(values=vals, set_value=data_row[idx])

            elif colname == "ts":
                # tuning step depend on frequency and market

                span.dropdown(
                    values=consts.tuning_steps_for_freq(
                        chan.freq, self.region
                    ),
                    set_value=data_row[idx],
                )

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

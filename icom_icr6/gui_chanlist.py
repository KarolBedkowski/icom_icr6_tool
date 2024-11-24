# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty

from tksheet import EventDataDict, functions

from . import consts, gui_genericlist, model

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

    def __repr__(self) -> str:
        return f"ROW: data={self.data!r} channel={self.channel}"

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
        current_val = data[col]
        if current_val == val or (current_val == "" and val is None):
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

        return self._extracts_cols(channel.to_record())


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


class ChannelsList(gui_genericlist.GenericList[Row, model.Channel]):
    _ROW_CLASS: type[gui_genericlist.BaseRow] = Row

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)

        self.on_channel_bank_validate: BankPosValidator | None = None

    def set_hide_canceller(self, *, hide: bool) -> None:
        canc_columns = [
            self.colmap[c] - 1 for c in ("canceller", "canceller freq")
        ]

        if hide:
            self.sheet.hide_columns(canc_columns)
        else:
            self.sheet.show_columns(canc_columns)

    def _on_validate_edits(self, event: EventDataDict) -> object:  # noqa:C901
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
                value = (
                    model.fix_offset(chan.freq, off)
                    if (off := int(value))
                    else 0
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
            values=consts.tuning_steps_for_freq(chan.freq),
        )

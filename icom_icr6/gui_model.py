# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.
# ruff: noqa: PLR2004,PLR0911,C901,PLR0912,PLR0915

""" """

import logging
import tkinter as tk
import typing as ty

from . import consts, model
from .gui_widgets import (
    CheckboxPopup,
    ComboboxPopup,
    EntryPopup,
    NumEntryPopup,
    TableView2,
    TableViewColumn,
    TableViewModel,
    TableViewModelRow,
    UpdateCellResult,
)

CHANNEL_RANGES = [
    "0-99",
    "100-199",
    "200-299",
    "300-399",
    "400-499",
    "500-599",
    "600-699",
    "700-799",
    "800-899",
    "900-999",
    "1000-1099",
    "1100-1199",
    "1200-1299",
]

_LOG = logging.getLogger(__name__)


def get_index_or_default(
    values: list[str] | tuple[str, ...],
    value: str | None,
    default_value: int,
    empty_value: str = "",
) -> int:
    if empty_value is None or value == empty_value or value is None:
        return default_value

    try:
        return values.index(value)
    except ValueError:
        return default_value


def get_or_default(
    values: list[str] | tuple[str, ...],
    index: int,
    empty_value: str = "",
) -> str:
    try:
        return values[index]
    except IndexError:
        return empty_value


class ChannelModel:
    def __init__(self) -> None:
        self.number = 0
        self.freq = tk.IntVar()
        self.name = tk.StringVar()
        self.mode = tk.StringVar()
        self.ts = tk.StringVar()
        self.af = tk.IntVar()
        self.attn = tk.IntVar()
        self.vsc = tk.IntVar()
        self.skip = tk.StringVar()

        self.duplex = tk.StringVar()
        self.offset = tk.IntVar()
        self.tone_mode = tk.StringVar()
        self.tsql_freq = tk.StringVar()
        self.dtsc = tk.StringVar()
        self.polarity = tk.StringVar()

        self.bank = tk.StringVar()
        self.bank_pos = tk.IntVar()

    def reset(self) -> None:
        self.name.set("")
        self.freq.set(0)
        self.mode.set("")
        self.ts.set("")
        self.af.set(0)
        self.attn.set(0)
        self.vsc.set(0)
        self.skip.set("")
        self.duplex.set("")
        self.offset.set(0)
        self.tone_mode.set("")
        self.tsql_freq.set("")
        self.dtsc.set("")
        self.polarity.set("")
        self.bank.set("")
        self.bank_pos.set(0)

    def fill(self, chan: model.Channel) -> None:
        self.number = chan.number
        if chan.hide_channel:
            self.reset()
            return

        self.name.set(chan.name.rstrip())
        self.freq.set(chan.freq // 1000)
        self.mode.set(consts.MODES[chan.mode])
        self.ts.set(consts.STEPS[chan.tuning_step])
        self.af.set(1 if chan.af_filter else 0)
        self.attn.set(1 if chan.attenuator else 0)
        self.vsc.set(1 if chan.vsc else 0)
        self.skip.set(consts.SKIPS[chan.skip])
        try:
            self.duplex.set(consts.DUPLEX_DIRS[chan.duplex])
        except IndexError:
            self.duplex.set("")
        self.offset.set(chan.offset // 1000)
        try:
            self.tone_mode.set(consts.TONE_MODES[chan.tone_mode])
        except IndexError:
            self.tone_mode.set("")
        try:
            self.tsql_freq.set(consts.CTCSS_TONES[chan.tsql_freq])
        except IndexError:
            self.tsql_freq.set("")
        try:
            self.dtsc.set(consts.DTCS_CODES[chan.dtsc])
        except IndexError:
            self.dtsc.set("")
        try:
            self.polarity.set(consts.POLARITY[chan.polarity])
        except IndexError:
            self.polarity.set("")
        try:
            self.bank.set(consts.BANK_NAMES[chan.bank])
            self.bank_pos.set(chan.bank_pos)
        except IndexError:
            self.bank.set("")
            self.bank_pos.set(0)

    def update_channel(self, chan: model.Channel) -> None:
        if freq := self.freq.get():
            chan.freq = freq * 1000
        else:
            raise ValueError

        chan.name = self.name.get().rstrip()[:6]
        # TODO: better default settings for freq?
        if mode := self.mode.get():
            chan.mode = consts.MODES.index(mode)
        elif chan.freq > 110:  # TODO: check
            chan.mode = 0
        elif chan.freq > 68:
            chan.mode = 1
        elif chan.freq > 30:
            chan.mode = 0
        else:
            chan.mode = 2

        if ts := self.ts.get():
            chan.tuning_step = consts.STEPS.index(ts)
        else:
            chan.tuning_step = 0

        chan.af_filter = self.af.get() == 1
        chan.attenuator = self.attn.get() == 1
        chan.vsc = self.vsc.get() == 1
        chan.skip = consts.SKIPS.index(self.skip.get())
        chan.duplex = consts.DUPLEX_DIRS.index(self.duplex.get())
        chan.offset = self.offset.get() * 1000
        chan.tone_mode = consts.TONE_MODES.index(self.tone_mode.get())
        chan.tsql_freq = get_index_or_default(
            consts.CTCSS_TONES, self.tsql_freq.get(), 63
        )
        chan.dtsc = get_index_or_default(
            consts.DTCS_CODES, self.dtsc.get(), 127
        )
        chan.polarity = get_index_or_default(
            consts.POLARITY, self.polarity.get(), 0
        )
        if (bank := self.bank.get()) == "":
            chan.bank = 31
            chan.bank_pos = 0
        else:
            chan.bank = consts.BANK_NAMES.index(bank)
            chan.bank_pos = self.bank_pos.get()

    def validate(self) -> list[str]:
        errors = []
        if not model.validate_frequency(self.freq.get() * 1000):
            errors.append("Invalid frequency")

        return errors


def yes_no(value: bool | None) -> str:
    match value:
        case None:
            return ""
        case True:
            return "yes"
        case False:
            return "no"


def name_validator(char: str, value: str) -> bool:
    if not value:
        return True

    if char.upper() not in consts.VALID_CHAR:
        return False

    try:
        model.validate_name(value)
    except ValueError:
        return False

    return True


class ChannelsListModel(TableViewModel[model.Channel | None]):
    def __init__(self, radio_memory: model.RadioMemory) -> None:
        super().__init__(self._columns())
        self._radio_memory = radio_memory

    def _columns(self) -> ty.Iterable[TableViewColumn]:
        tvc = TableViewColumn
        return (
            tvc("num", "Num", tk.E, 30),
            tvc("freq", "Freq", tk.E, 80),
            tvc("mode", "Mode", tk.CENTER, 25),
            tvc("name", "Name", tk.W, 50),
            tvc("af", "AF", tk.CENTER, 25),
            tvc("att", "ATT", tk.CENTER, 25),
            tvc("ts", "TS", tk.CENTER, 40),
            tvc("duplex", "DUP", tk.CENTER, 25),
            tvc("offset", "Offset", tk.E, 60),
            tvc("skip", "Skip", tk.CENTER, 25),
            tvc("vsc", "VSC", tk.CENTER, 25),
            tvc("tone", "Tone", tk.CENTER, 30),
            tvc("tsql", "TSQL", tk.E, 40),
            tvc("dtsc", "DTSC", tk.E, 30),
            tvc("polarity", "Polarity", tk.CENTER, 35),
            tvc("bank", "Bank", tk.CENTER, 25),
            tvc("bank_pos", "Bank pos", tk.W, 25),
        )

    def _data2iid(self, chan: model.Channel) -> str:
        return str(chan.number)

    def get_editor(
        self,
        row: int,
        column: int,
        value: str,
        parent: TableView2[model.Channel | None],
    ) -> tk.Widget | None:
        coldef = self.columns[column]
        data_row = self.data[row]
        if not data_row:
            return None

        iid = self._data2iid(data_row)
        chan = self.data[row]
        if chan is None:
            return None

        _LOG.debug(
            "get_editor: row=%d[%r], col=%d[%s], value=%r, chan=%r",
            row,
            iid,
            column,
            coldef.colid,
            value,
            chan,
        )
        match coldef.colid:
            case "num":  # num
                return None

            case "af" | "att" | "vsc":
                return CheckboxPopup(parent, iid, column, value)

            case "mode":
                return ComboboxPopup(parent, iid, column, value, consts.MODES)

            case "ts":
                return ComboboxPopup(parent, iid, column, value, consts.STEPS)

            case "duplex":
                return ComboboxPopup(
                    parent, iid, column, value, consts.DUPLEX_DIRS
                )

            case "skip":
                return ComboboxPopup(parent, iid, column, value, consts.SKIPS)

            case "tone":
                return ComboboxPopup(
                    parent, iid, column, value, consts.TONE_MODES
                )

            case "tsql":
                if chan.tone_mode not in (1, 2):
                    return None

                return ComboboxPopup(
                    parent, iid, column, value, consts.CTCSS_TONES
                )

            case "dtsc":
                if chan.tone_mode not in (3, 4):
                    return None

                return ComboboxPopup(
                    parent, iid, column, value, consts.DTCS_CODES
                )

            case "polarity":
                if chan.tone_mode not in (3, 4):
                    return None

                return ComboboxPopup(
                    parent, iid, column, value, consts.POLARITY
                )
            case "offset":
                if not chan.duplex:
                    return None

                return NumEntryPopup(
                    parent, iid, column, value, min_val=0, max_val=159995
                )

            case "name":
                return EntryPopup(parent, iid, column, value).with_validator(
                    name_validator
                )

            case "bank":
                return ComboboxPopup(
                    parent, iid, column, value, list(consts.BANK_NAMES)
                )

            case "bank_pos":
                if chan.bank == consts.BANK_NOT_SET:
                    return None

                return NumEntryPopup(parent, iid, column, value, max_val=99)

            case "freq":
                return NumEntryPopup(
                    parent,
                    iid,
                    column,
                    value,
                    max_val=consts.MAX_FREQUENCY // 1000,
                )

        return None

    def update_cell(
        self,
        row: int,  # row
        column: int,
        value: str | None,  # new value
    ) -> tuple[UpdateCellResult, model.Channel | None]:
        chan = self.data[row]
        if chan is None:
            return UpdateCellResult.NOOP, None

        _LOG.debug("update chan: %r", chan)

        coldef = self.columns[column]
        if (not chan.freq or chan.hide_channel) and coldef.colid != "freq":
            return UpdateCellResult.NOOP, None

        res = UpdateCellResult.UPDATE_ROW

        match coldef.colid:
            case "num":  # num
                return UpdateCellResult.NOOP, None

            case "freq":
                chan.freq = (
                    model.fix_frequency(int(value) * 1000) if value else 0
                )
                if chan.freq and chan.hide_channel:
                    chan.hide_channel = False
                    chan.mode = model.default_mode_for_freq(chan.freq)

            case "mode":
                chan.mode = consts.MODES.index(value) if value else 0

            case "name":
                chan.name = model.fix_name(value or "")

            case "af":
                chan.af_filter = value == "yes"

            case "att":
                chan.attenuator = value == "yes"

            case "ts":
                chan.tuning_step = consts.STEPS.index(value) if value else 0

            case "duplex":
                chan.duplex = consts.DUPLEX_DIRS.index(value) if value else 0

            case "offset":
                chan.offset = int(value or 0) * 1000

            case "skip":
                chan.skip = consts.SKIPS.index(value) if value else 0

            case "tone":
                chan.tone_mode = get_index_or_default(
                    consts.TONE_MODES, value, 0
                )

            case "tsql":
                chan.tsql_freq = get_index_or_default(
                    consts.CTCSS_TONES, value, 63
                )

            case "dtsc":
                chan.dtsc = get_index_or_default(consts.DTCS_CODES, value, 127)

            case "polarity":
                chan.polarity = get_index_or_default(consts.POLARITY, value, 0)

            case "vsc":
                chan.vsc = value == "yes"

            case "bank":
                prev_bank = chan.bank
                chan.bank = get_index_or_default(
                    list(consts.BANK_NAMES), value, consts.BANK_NOT_SET
                )
                if chan.bank not in (prev_bank, consts.BANK_NOT_SET):
                    bank = self._radio_memory.get_bank(chan.bank)
                    pos = bank.find_free_slot()
                    chan.bank_pos = pos if pos is not None else 99

            case "bank_pos":
                bank_pos = 0
                if chan.bank != consts.BANK_NOT_SET:
                    bank_pos = int(value or 0)
                    bank = self._radio_memory.get_bank(chan.bank)
                    if bank.channels[bank_pos] != chan.number:
                        # selected slot is used by another channel
                        if chan.number in bank.channels:
                            # do not update
                            bank_pos = chan.bank_pos
                        else:
                            # find unused next slot
                            pos = bank.find_free_slot(bank_pos)
                            if pos is None:
                                # find first unused slot
                                pos = bank.find_free_slot()

                            if pos is not None:
                                bank_pos = pos
                            else:  # not found unused slot - replace
                                res = UpdateCellResult.UPDATE_ALL

                chan.bank_pos = bank_pos

            case _:
                return UpdateCellResult.NOOP, None

        _LOG.debug("new chan: %r", chan)
        self._radio_memory.set_channel(chan)
        self.data[row] = chan
        return res, chan

    def data2row(self, channel: model.Channel | None) -> TableViewModelRow:
        if channel is None:
            return ("",)

        if channel.hide_channel or not channel.freq:
            return (str(channel.number),)

        try:
            bank = consts.BANK_NAMES[channel.bank]
            bank_pos = str(channel.bank_pos)
        except IndexError:
            bank = bank_pos = ""

        return (
            str(channel.number),
            str(channel.freq // 1000),
            consts.MODES[channel.mode],
            channel.name.rstrip(),
            yes_no(channel.af_filter),
            yes_no(channel.attenuator),
            consts.STEPS[channel.tuning_step],
            consts.DUPLEX_DIRS[channel.duplex],
            str(channel.offset // 1000) if channel.duplex else "",
            consts.SKIPS[channel.skip],
            yes_no(channel.vsc),
            consts.TONE_MODES[channel.tone_mode],
            get_or_default(consts.CTCSS_TONES, channel.tsql_freq)
            if channel.tone_mode in (1, 2)
            else "",
            get_or_default(consts.DTCS_CODES, channel.dtsc)
            if channel.tone_mode in (3, 4)
            else "",
            consts.POLARITY[channel.polarity]
            if channel.tone_mode in (3, 4)
            else "",
            bank,
            bank_pos,
        )


class ListVar(tk.StringVar):
    def __init__(self, values: list[str]) -> None:
        super().__init__()
        self._values = values

    def set_raw(self, value: int | None) -> None:
        if value is not None:
            self.set(self._values[value])
        else:
            self.set("")

    def get_raw(self) -> int:
        return self._values.index(self.get())


class BoolVar(tk.IntVar):
    def set_raw(self, value: object) -> None:
        self.set(1 if value else 0)

    def get_raw(self) -> bool:
        return self.get() == 1

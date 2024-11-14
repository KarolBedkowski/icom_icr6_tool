# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from abc import ABC
from collections import UserList
from dataclasses import dataclass

from tksheet import (
    Dropdown,
    EventDataDict,
    Formatter,
    Sheet,
    bool_formatter,
    float_formatter,
    formatter,
    functions,
    int_formatter,
    num2alpha,
)

from . import consts, model

_LOG = logging.getLogger(__name__)


class Row(UserList[object]):
    def __init__(self, channel: model.Channel) -> None:
        self.channel = channel
        super().__init__(self._from_channel(channel))

    def __setitem__(self, idx: int, val: object) -> None:
        if val == self.data[idx]:
            return

        chan = self.channel

        if (not chan.freq or chan.hide_channel) and idx != 1:
            return

        match idx:
            case 0:
                return
            case 1:  # freq
                if val is None:
                    chan.freq = 0
                    chan.hide_channel = True
                    self.data = self._from_channel(chan)
                    return

                assert isinstance(val, int)
                chan.freq = val
                chan.hide_channel = False
                chan.mode = model.default_mode_for_freq(chan.freq)
                self.data = self._from_channel(chan)
                return

            case 2:  # mode
                if val is None:
                    val = 4
                assert isinstance(val, int)
                chan.mode = val
            case 3:  # name
                chan.name = str(val or "")
            case 4:  # af_filter
                assert isinstance(val, bool)
                chan.af_filter = val
            case 5:  # attenuator
                assert isinstance(val, bool)
                chan.attenuator = val
            case 6:
                if val is None:
                    val = 14
                assert isinstance(val, int)
                chan.tuning_step = val
            case 7:
                val = val or 0
                assert isinstance(val, int)
                chan.duplex = val
            case 8:
                val = val or 0
                assert isinstance(val, int)
                chan.offset = val
            case 9:
                val = val or 0
                assert isinstance(val, int)
                chan.skip = val
            case 10:
                val = val or False
                assert isinstance(val, bool)
                chan.vsc = val
            case 11:
                val = val or 0
                assert isinstance(val, int)
                chan.tone_mode = val
            case 12:
                val = val or 0
                assert isinstance(val, int)
                chan.tsql_freq = val
            case 13:
                val = val or 0
                assert isinstance(val, int)
                chan.dtsc = val
            case 14:
                val = val or 0
                assert isinstance(val, int)
                chan.polarity = val
            case 15:
                if val is None:
                    val = consts.BANK_NOT_SET
                assert isinstance(val, int)
                chan.bank = val
            case 16:
                val = val or 0
                assert isinstance(val, int)
                chan.bank_pos = val
            case 17:
                val = val or 0
                assert isinstance(val, int)
                chan.canceller = val
            case 18:
                val = val or 300
                assert isinstance(val, int)
                chan.canceller_freq = val // 10

        super().__setitem__(idx, val)

    def _from_channel(self, channel: model.Channel) -> list[object]:
        if channel is None:
            return [""] * 19

        if channel.hide_channel or not channel.freq:
            return [channel.number, *([""] * 18)]

        return [
            channel.number,
            channel.freq,
            channel.mode,
            channel.name.rstrip(),
            channel.af_filter,
            channel.attenuator,
            channel.tuning_step,
            channel.duplex,
            channel.offset,
            channel.skip,
            channel.vsc,
            channel.tone_mode,
            channel.tsql_freq,
            channel.dtsc,
            channel.polarity,
            channel.bank if channel.bank != consts.BANK_NOT_SET else None,
            channel.bank_pos,
            channel.canceller,
            channel.canceller_freq * 10,
        ]

    def delete(self) -> None:
        self.channel.hide_channel = True
        self.channel.freq = 0
        self.data = self._from_channel(self.channel)


def to_int(o: object, **_kwargs: object) -> int:
    if isinstance(o, int):
        return o

    if isinstance(o, str):
        return int(o.replace(" ", ""))

    return int(o)  # type: ignore


def format_freq(freq: int, **_kwargs: object) -> str:
    return f"{freq:_}".replace("_", " ")


def yes_no(value: bool | None) -> str:
    match value:
        case None:
            return ""
        case True:
            return "yes"
        case False:
            return "no"


def dropdown_formatter(values: list[str]) -> dict[str, object]:
    def format_function(val: str, **_kwargs: object) -> int:
        return values.index(val)

    def to_str_function(v: int, **_kwargs: object) -> str:
        try:
            return values[v]
        except IndexError:
            _LOG.warn("values: %r, v: %r, %r", values, v, _kwargs)
            return ""

    return formatter(  # type: ignore
        datatypes=(int,),
        format_function=format_function,
        to_str_function=to_str_function,
        invalid_value="",
    )


def dropdown_select_function(
    values: ty.Sequence[str],
) -> ty.Callable[[dict[str, object]], None]:
    def func(event_data: EventDataDict) -> None:
        event_data["value"] = values.index(event_data["value"])

    return func


class IndexedDropdown(Dropdown):
    pass


# def dropbox_modified_function(


class Column(ty.NamedTuple):
    colid: str
    title: str
    anchor: str
    width: int


class ChannelsList(tk.Frame):
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

        self.columns = self._columns()
        self._configure()
        self.on_record_update: (
            ty.Callable[[ty.Collection[Row]], None] | None
        ) = None
        self.on_record_selected: ty.Callable[[list[Row]], None] | None = None

    def set_data(self, data: ty.Iterable[model.Channel]) -> None:
        self.sheet.set_sheet_data(list(map(Row, data)))
        self.sheet.set_all_column_widths()
        for row in range(len(self.sheet.data)):
            self._update_row_states(row)

    def _columns(self) -> tuple[Column, ...]:
        return (
            Column("num", "Num", tk.E, 30),
            Column("freq", "Frequency", tk.E, 200),
            Column("mode", "Mode", tk.CENTER, 25),
            Column("name", "Name", tk.W, 50),
            Column("af", "AF", tk.CENTER, 25),
            Column("att", "ATT", tk.CENTER, 25),
            Column("ts", "Tuning Step", tk.CENTER, 40),
            Column("duplex", "DUP", tk.CENTER, 25),
            Column("offset", "Offset", tk.E, 60),
            Column("skip", "Skip", tk.CENTER, 25),
            Column("vsc", "VSC", tk.CENTER, 25),
            Column("tone", "Tone", tk.CENTER, 30),
            Column("tsql", "TSQL", tk.E, 40),
            Column("dtsc", "DTSC", tk.E, 30),
            Column("polarity", "Polarity", tk.CENTER, 35),
            Column("bank", "Bank", tk.CENTER, 25),
            Column("bank_pos", "Bank pos", tk.W, 25),
            Column("canc", "Canceller", tk.CENTER, 30),
            Column("canc_freq", "Canceller freq", tk.E, 40),
        )

    def _setup_dropbox(self, col: int, values: list[str]) -> None:
        def selection_function(event_data: EventDataDict) -> None:
            event_data["value"] = values.index(event_data["value"])

        def format_function(val: str, **_kwargs: object) -> int:
            return values.index(val)

        def to_str_function(v: int, **_kwargs: object) -> str:
            try:
                return values[v]
            except IndexError:
                _LOG.warn("values: %r, v: %r, %r", values, v, _kwargs)
                return ""

        fmtr = formatter(
            datatypes=(int,),
            format_function=format_function,
            to_str_function=to_str_function,
            invalid_value="",
        )

        self.sheet[num2alpha(col)].dropdown(
            values=values,
            state="",
            selection_function=selection_function,
        ).align("center").format(fmtr)

    def _setup_dropbox_bank(self, col: int) -> None:
        values: list[str] = ["", *consts.BANK_NAMES]

        def func(event_data: EventDataDict) -> None:
            if val := event_data["value"]:
                event_data["value"] = values.index(val) - 1
            else:
                event_data["value"] = consts.BANK_NOT_SET

        def format_function(val: str, **_kwargs: object) -> int:
            return values.index(val) - 1 if val else consts.BANK_NOT_SET

        def to_str_function(v: int, **_kwargs: object) -> str:
            try:
                return values[v + 1]
            except IndexError:
                return ""

        fmtr = formatter(
            datatypes=(int,),
            format_function=format_function,
            to_str_function=to_str_function,
            invalid_value="",
        )

        self.sheet[num2alpha(col)].dropdown(
            values=values,
            state="",
            selection_function=func,
        ).align("center").format(fmtr)

    def _configure(self) -> None:
        self.sheet.headers([c.title for c in self.columns])

        self.sheet[num2alpha(0)].format(int_formatter()).align("right")
        self.sheet[num2alpha(1)].format(
            int_formatter(
                format_function=to_int,
                to_str_function=format_freq,
                invalid_value="",
            )
        ).align("right")
        self._setup_dropbox(2, consts.MODES)
        self.sheet[num2alpha(4)].checkbox().align("center")
        self.sheet[num2alpha(5)].checkbox().align("center")
        self._setup_dropbox(6, consts.STEPS)
        self._setup_dropbox(7, consts.DUPLEX_DIRS)
        self.sheet[num2alpha(8)].format(int_formatter(invalid_value="")).align(
            "right"
        )
        self._setup_dropbox(9, consts.SKIPS)
        self.sheet[num2alpha(10)].checkbox().align("center")
        self._setup_dropbox(11, consts.TONE_MODES)
        self._setup_dropbox(12, consts.CTCSS_TONES)
        self._setup_dropbox(13, consts.DTCS_CODES)
        self._setup_dropbox(14, consts.POLARITY)
        self._setup_dropbox_bank(15)
        self.sheet[num2alpha(16)].format(
            int_formatter(invalid_value="")
        ).align("center")
        self._setup_dropbox(17, consts.CANCELLER)
        self.sheet[num2alpha(18)].format(
            int_formatter(invalid_value="")
        ).align("right")

        self.sheet.row_index(0)
        self.sheet.hide_columns(0)

    def _on_sheet_modified(self, event: EventDataDict) -> None:
        #if event.eventname == "edit_table":
        #    return

        _LOG.debug("_on_sheet_modified: %r", event)

        # if not self.on_record_update or not event.cells.table:
        #    return

        #        for r, _c in event.cells.table:
        #            row = self.sheet.data[r]

        # TODO: distinct
        data = [self.sheet.data[r] for (r, _c) in event.cells.table]

        for r, _c in event.cells.table:
            self._update_row_states(r)

        if data and self.on_record_update:
            self.on_record_update(data)

    def _on_validate_edits(self, event: EventDataDict) -> object:
        if event.eventname != "end_edit_table":
            return None

        _LOG.debug("_on_validate_edits: %r", event)

        column = self.columns[event.column + 1]  # FIXME: visible cols
        row = self.sheet.data[event.row]
        value = event.value

        try:
            match column[0]:
                case "freq":
                    return model.fix_frequency(int(value))

                case "name":
                    return model.fix_name(value)

                case "offset":
                    if not row.duplex:
                        return None

                    assert isinstance(value, int)
                    return max(min(value, consts.MAX_OFFSET), 0)

                case "canc_freq":
                    assert isinstance(value, int)
                    return max(
                        min((value // 10) * 10, consts.CANCELLER_MAX_FREQ),
                        consts.CANCELLER_MIN_FREQ,
                    )

                case "bank_pos":
                    # TODO: validate
                    return max(min(value, 99), 0)

        except ValueError:
            return None

        return event.value

    def _on_sheet_select(self, event: EventDataDict) -> None:
        _LOG.debug("_on_sheet_select: %r", event)
        row, col = event.selected.row, event.selected.column
        column = self.columns[col + 1]  # FIXME: visible cols
        col += 1
        data_row = self.sheet.data[row]

        if not data_row[1] and col != 1:
            functions.set_readonly(
                self.sheet.MT.cell_options, (row, col), readonly=True
            )
            return

        functions.set_readonly(
            self.sheet.MT.cell_options, (row, col), readonly=False
        )
        if column[0] == "ts":
            self.sheet.set_dropdown_values(
                row,
                col,
                values=model.tuning_steps_for_freq(data_row[1]),
            )  # freq

        if self.on_record_selected:
            sel_box = event.selected.box
            rows = [
                self.sheet.data[r]
                for r in range(sel_box.from_r, sel_box.upto_r)
            ]
            self.on_record_selected(rows)

    def selected_rows(self) -> list[Row]:
        return [
            self.sheet.data[r]
            for r in self.sheet.get_selected_rows(get_cells_as_rows=True)
        ]

    def _on_delete(self, event: EventDataDict) -> None:
        data = []
        if event.selected.type_ == "rows":
            box = event.selected.box
            for r in range(box.from_r, box.upto_r):
                row = self.sheet.data[r]
                row.delete()
                data.append(row)
                self._update_row_states(r)

        elif event.selected.type_ == "cells":
            r = event.selected.row
            self.sheet[r, event.selected.column + 1].data = ""
            self._update_row_states(r)
            data.append(self.sheet.data[r])

        if data and self.on_record_update:
            self.on_record_update(data)

    def _update_row_states(self, row: int) -> None:
        data_row = self.sheet.data[row]
        chan = data_row.channel
        self.sheet.highlight_cells(
            row, column=8, fg="black" if chan.duplex else "gray"
        )
        self.sheet.highlight_cells(
            row, column=12, fg="black" if chan.tone_mode in (1, 2) else "gray"
        )
        self.sheet.highlight_cells(
            row, column=13, fg="black" if chan.tone_mode in (3, 4) else "gray"
        )
        self.sheet.highlight_cells(
            row, column=14, fg="black" if chan.tone_mode in (3, 4) else "gray"
        )
        self.sheet.highlight_cells(
            row,
            column=16,
            fg="black" if chan.bank != consts.BANK_NOT_SET else "gray",
        )

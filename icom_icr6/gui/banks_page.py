# Copyright © 2024-2025 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

"""
Notebook tab containing banks and channels.
"""

import itertools
import logging
import tkinter as tk
import typing as ty
from tkinter import messagebox, ttk

from icom_icr6 import consts, expimp, fixers, model, model_support, validators
from icom_icr6.change_manager import ChangeManeger
from icom_icr6.radio_memory import RadioMemory

from . import banks_channelslist, gui_model
from .widgets import (
    new_checkbox,
    new_entry,
)

_LOG = logging.getLogger(__name__)


class BanksPage(tk.Frame):
    def __init__(self, parent: tk.Widget, cm: ChangeManeger) -> None:
        super().__init__(parent)
        self._parent = parent
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._bank_name = tk.StringVar()
        self._bank_name.trace("w", self._on_bank_name_changed)  # type: ignore
        self._bank_link = gui_model.BoolVar()
        self._bank_link.trace("w", self._on_bank_link_changed)  # type: ignore
        self._change_manager = cm
        self._in_paste = False
        self._last_selected_bank = 0
        self._last_selected_pos = [0] * consts.NUM_BANKS
        self._banks_stats: list[str] = []
        self._banks = tk.StringVar(value=self._banks_stats)  # type: ignore

        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        banks = self._banks_list = tk.Listbox(
            pw, selectmode=tk.SINGLE, width=15, listvariable=self._banks
        )

        banks.bind("<<ListboxSelect>>", self._on_bank_select)
        pw.add(banks, weight=0)

        frame = tk.Frame(pw)
        self._create_bank_fields(frame)
        self._create_chan_list(frame)
        pw.add(frame, weight=1)

        pw.pack(expand=True, fill=tk.BOTH, side=tk.TOP, padx=12, pady=12)

        self._update_banks_list()

    def update_tab(
        self, bank: int | None = None, bank_pos: int | None = None
    ) -> None:
        # hide canceller in global models
        self._chan_list.set_radio_memory(self._change_manager.rm)
        self._update_banks_list()

        if bank is None:
            bank = self._last_selected_bank

        if bank_pos is None:
            bank_pos = self._last_selected_pos[bank]

        self.select(bank, bank_pos, force=True)

    def select(
        self, bank: int, bank_pos: int | None = None, *, force: bool = False
    ) -> None:
        sel_bank = self._banks_list.curselection()

        self._last_selected_bank = bank
        if bank_pos is not None:
            self._last_selected_pos[bank] = bank_pos

        if (
            (sel_bank and bank == sel_bank[0])
            and bank_pos is not None
            and not force
        ):
            self._chan_list.selection_set([bank_pos])
            return

        self._banks_list.selection_clear(0, consts.NUM_BANKS)
        self._banks_list.selection_set(bank)
        self._update_chan_list(select=bank_pos)

    def reset(self) -> None:
        self._chan_list.set_radio_memory(self._change_manager.rm)
        self._last_selected_bank = 0
        self._last_selected_pos = [0] * consts.NUM_BANKS
        self._update_banks_list()
        self._banks_list.selection_set(0)
        self._update_chan_list()

    @property
    def _radio_memory(self) -> RadioMemory:
        return self._change_manager.rm

    def _create_bank_fields(self, frame: tk.Frame) -> None:
        fields = tk.Frame(frame)
        fields.columnconfigure(0, weight=0)
        fields.columnconfigure(1, weight=0)
        fields.columnconfigure(2, weight=0)
        fields.columnconfigure(3, weight=0)

        validator = self.register(validate_bank_name)
        self._field_bank_name = new_entry(
            fields, 0, 0, "Bank name: ", self._bank_name, validator=validator
        )
        self._field_bank_link = new_checkbox(
            fields, 0, 2, "Bank link", self._bank_link
        )

        fields.pack(side=tk.TOP, fill=tk.X)

    def _create_chan_list(self, frame: tk.Frame) -> None:
        self._chan_list = banks_channelslist.ChannelsList(
            frame, self._change_manager.rm
        )
        self._chan_list.pack(side=tk.TOP, expand=True, fill=tk.BOTH, pady=6)

        self._chan_list.on_record_selected = self._on_channel_select
        self._chan_list.on_record_update = self._on_channel_update
        self._chan_list.sheet.bind("<Control-c>", self._on_channel_copy)
        self._chan_list.sheet.bind("<Control-v>", self._on_channel_paste)

        bframe = tk.Frame(frame)
        self._btn_sort = ttk.Button(
            bframe,
            text="Sort...",
            command=self._on_btn_sort,
            state="disabled",
        )
        self._btn_sort.pack(side=tk.LEFT)

        bframe.pack(side=tk.BOTTOM, fill=tk.X)

    def _on_bank_select(self, _event: tk.Event) -> None:  # type: ignore
        if sel_bank := self._banks_list.curselection():
            self._last_selected_bank = int(sel_bank[0])
        else:
            self._last_selected_bank = 0

        self._chan_list.reset(scroll_top=True)
        self._update_chan_list(
            select=self._last_selected_pos[self._last_selected_bank]
        )

    def _update_banks_list(self) -> None:
        banks = self._banks_list
        rm = self._radio_memory

        self._banks_stats = []
        for idx, bank in enumerate(self._radio_memory.banks):
            active = sum(bool(c) for c in rm.get_bank_channels(idx).channels)
            self._banks_stats.append(_bank_list_label(idx, bank.name, active))

        self._banks.set(self._banks_stats)  # type: ignore

        banks.selection_set(self._last_selected_bank)

    def _update_chan_list(
        self,
        _event: tk.Event | None = None,  # type: ignore
        *,
        select: int | None = None,
    ) -> None:
        selected_bank = self._last_selected_bank

        bank = self._radio_memory.banks[selected_bank]
        self._bank_name.set(bank.name.rstrip())

        bl = self._radio_memory.bank_links
        self._bank_link.set_raw(bl[selected_bank])

        channels = self._radio_memory.get_bank_channels(selected_bank)
        self._chan_list.set_data(
            [
                self._radio_memory.channels[channum]
                if channum is not None
                else None
                for channum in channels.channels
            ]
        )

        self._field_bank_name["state"] = "normal"
        self._field_bank_link["state"] = "normal"
        self._show_stats()

        if select is not None:
            self.update_idletasks()
            self.after(10, lambda: self._chan_list.selection_set([select]))

    def _show_stats(self) -> None:
        selected_bank = self._last_selected_bank

        rm = self._radio_memory
        bank = rm.banks[selected_bank]
        active = sum(
            bool(c) for c in rm.get_bank_channels(selected_bank).channels
        )
        self._parent.set_status(f"Active channels in bank: {active}")  # type: ignore
        self._banks_stats[selected_bank] = _bank_list_label(
            selected_bank, bank.name, active
        )
        self._banks.set(self._banks_stats)  # type: ignore

    def _on_bank_name_changed(self, _var: str, _idx: str, _op: str) -> None:
        bank = self._radio_memory.banks[self._last_selected_bank]
        name = self._bank_name.get()
        fixed_name = fixers.fix_name(name)
        if bank.name == fixed_name:
            return

        if fixed_name != name:
            self._bank_name.set(fixed_name)

        bank = bank.clone()
        bank.name = name
        self._change_manager.set_bank(bank)
        self._change_manager.commit()
        self._update_banks_list()

    def _on_bank_link_changed(self, _var: str, _idx: str, _op: str) -> None:
        bank = self._last_selected_bank
        new_val = self._bank_link.get_raw()
        bl = self._radio_memory.bank_links
        if new_val == bl[bank]:
            return

        bl = bl.clone()
        bl[bank] = new_val
        self._change_manager.set_bank_links(bl)
        self._change_manager.commit()

    def _on_channel_select(
        self, rows: list[banks_channelslist.RowType]
    ) -> None:
        self._btn_sort["state"] = "normal" if len(rows) > 1 else "disabled"
        self._last_selected_pos[self._last_selected_bank] = rows[0].rownum

        if _LOG.isEnabledFor(logging.DEBUG):
            for row in rows:
                _LOG.debug("chan selected: %r", row)

    def _on_channel_update(
        self, action: str, rows: ty.Collection[banks_channelslist.RowType]
    ) -> None:
        match action:
            case "delete":
                self._do_delete_channels(rows)

            case "update":
                self._do_update_channels(rows)

            case "move":
                self._do_move_channels(rows)

    def _do_delete_channels(
        self, rows: ty.Collection[banks_channelslist.RowType]
    ) -> None:
        if not messagebox.askyesno(
            "Delete channel",
            "Delete channel configuration from bank?",
            icon=messagebox.WARNING,
        ):
            return

        channels = []
        bank_pos = []
        for row in rows:
            if chan := row.obj:
                _LOG.debug("_do_delete_channels: row=%r, chan=%r", row, chan)
                bank_pos.append(row.rownum)
                chan = chan.clone()
                chan.clear_bank()
                channels.append(chan)

        self._change_manager.set_channel(*channels)
        self._change_manager.commit()

        for pos in bank_pos:
            self._chan_list.update_data(pos, None)

    def _do_update_channels(
        self, rows: ty.Collection[banks_channelslist.RowType]
    ) -> None:
        # modified channels
        channels = list(
            itertools.chain.from_iterable(map(self.__do_update_channel, rows))
        )

        self._change_manager.set_channel(*channels)

        if not self._in_paste:
            self._change_manager.commit()
            for chan in channels:
                self._chan_list.update_data(chan.bank_pos, chan)

    def __do_update_channel(
        self, row: banks_channelslist.RowType
    ) -> ty.Iterator[model.Channel]:
        _LOG.debug("__do_update_channel: row=%r", row)
        assert row.changes
        chan: model.Channel | None = None

        if "channel" in row.changes:
            if (new_chan_num := row.changes.get("channel")) is not None:
                # change channel in bankpos
                assert isinstance(new_chan_num, int)
                del row.changes["channel"]

                if (old_chan := row.obj) and old_chan.number != new_chan_num:
                    # clear old chan
                    old_chan = old_chan.clone()
                    old_chan.clear_bank()
                    yield old_chan

                # add chan to bank
                chan = self._radio_memory.channels[new_chan_num].clone()

            else:
                # remove channel from bank
                if (c := row.obj) is not None:
                    c = c.clone()
                    c.clear_bank()
                    yield c

                return

        if not row.obj and (freq := row.changes.get("freq")):
            # create new position with new channel by freq
            assert isinstance(freq, int)
            del row.changes["freq"]

            # empty pos, entered freq
            chan = self._radio_memory.find_first_hidden_channel()
            if not chan:
                # TODO: error? is this possible?
                return

            chan = chan.clone()
            chan.freq = freq

        if not chan:
            assert row.obj is not None
            chan = row.obj.clone()

        chan.bank = self._last_selected_bank
        chan.bank_pos = row.rownum

        # if new channel - make it visible
        if chan.hide_channel:
            # when hidden channel has no frequency; set 50MHz
            chan.freq = fixers.fix_frequency(chan.freq or 50_000_000)
            band = self._change_manager.rm.get_band_for_freq(chan.freq)
            chan.load_defaults_from_band(band)
            chan.hide_channel = False

        if row.changes:
            chan.from_record(row.changes)

        yield chan

    def _do_move_channels(
        self, rows: ty.Collection[banks_channelslist.RowType]
    ) -> None:
        channels = []
        for row in rows:
            if not row.obj:
                continue

            _LOG.debug("_do_move_channels: %r -> %d", row.obj, row.rownum)
            chan = row.obj.clone()
            chan.bank_pos = row.rownum
            channels.append(chan)

        if channels:
            self._change_manager.set_channel(*channels)
            self._change_manager.commit()
            for chan in channels:
                self._chan_list.update_data(chan.bank_pos, chan)

    def _on_channel_copy(self, _event: tk.Event) -> None:  # type: ignore
        selected = self._chan_list.sheet.get_currently_selected()
        if not selected:
            return

        res = None

        if selected.type_ == "rows":
            if rows := self._chan_list.selected_rows_data():
                channels = (chan for row in rows if (chan := row.obj))
                res = expimp.export_channel_str(channels)

        elif selected.type_ == "cells" and (
            data := self._chan_list.selected_data()
        ):
            res = expimp.export_table_as_string(data).strip()

        if res:
            gui_model.Clipboard.instance().put(res)

    def _on_channel_paste(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._chan_list.selection()
        if not sel:
            return

        self._in_paste = True

        clip = gui_model.Clipboard.instance()
        data = ty.cast(str, clip.get())
        try:
            # try import whole channels
            if not self._on_channel_paste_channels(
                self._last_selected_bank, sel, data
            ):
                # try import as plain data
                self._on_channel_paste_simple(data)

        except Exception as err:
            _LOG.exception("_on_channel_paste error")
            self._change_manager.abort()
            messagebox.showerror(
                "Paste data error", f"Clipboard content can't be pasted: {err}"
            )

        else:
            self._change_manager.commit()
            self._update_chan_list()

        self._in_paste = False

    def _on_channel_paste_channels(
        self, selected_bank: int, sel_pos: tuple[int, ...], data: str
    ) -> bool:
        try:
            rows = list(expimp.import_channels_str(data))
        except ValueError:
            return False

        bank_channels = self._radio_memory.get_bank_channels(selected_bank)

        # special case - when in clipboard is one record and selected  many-
        # duplicate
        if len(sel_pos) > 1 and len(rows) == 1:
            row = rows[0]
            for spos in sel_pos:
                if not self._paste_channel(
                    row, spos, selected_bank, bank_channels
                ):
                    break

        else:
            for pos, row in enumerate(rows, sel_pos[0]):
                if not self._paste_channel(
                    row, pos, selected_bank, bank_channels
                ):
                    break

                if pos % 100 == 99:  # noqa: PLR2004
                    break

        return True

    def _on_channel_paste_simple(self, data: str) -> None:
        if rows := expimp.import_str_as_table(data):
            self._chan_list.paste(rows)

    def _paste_channel(
        self,
        row: dict[str, object],
        pos: int,
        selected_bank: int,
        bank_channels: model.BankChannels,
    ) -> bool:
        if not row.get("freq"):
            return True

        chan_num = bank_channels[pos]
        if chan_num:
            chan = self._radio_memory.channels[chan_num]
        else:
            chan = self._radio_memory.find_first_hidden_channel()  # type: ignore
            if not chan:
                _LOG.warning("no hidden channel found")
                return False

        chan = chan.clone()
        # replace channel
        try:
            chan.from_record(row)
            chan.validate()
        except ValueError:
            _LOG.exception("import from clipboard error")
            _LOG.error("chan_num=%d, row=%r", chan_num, row)
            return False

            # replace
        _LOG.debug("replacing channel: %r", chan)

        chan.bank = selected_bank
        chan.bank_pos = pos
        chan.hide_channel = False
        self._change_manager.set_channel(chan)

        return True

    def _on_btn_sort(self) -> None:
        rows = self._chan_list.selected_rows_data()
        if len(rows) <= 1:
            return

        popup_menu = tk.Menu(self, tearoff=0)
        popup_menu.add_command(
            label="Sort by frequency", command=lambda: self._do_sort("freq")
        )

        popup_menu.add_command(
            label="Sort by name", command=lambda: self._do_sort("name")
        )
        popup_menu.add_command(
            label="Sort by name (empty first)",
            command=lambda: self._do_sort("name2"),
        )
        popup_menu.add_command(
            label="Sort by channel number",
            command=lambda: self._do_sort("channel"),
        )
        popup_menu.add_separator()
        popup_menu.add_command(
            label="Pack", command=lambda: self._do_sort("pack")
        )
        try:
            btn = self._btn_sort
            popup_menu.tk_popup(btn.winfo_rootx(), btn.winfo_rooty())
        finally:
            popup_menu.grab_release()

    def _do_sort(self, field: str) -> None:
        rows = self._chan_list.selected_rows_data()
        if len(rows) <= 1:
            return

        channels = [
            chan.clone() if (chan := row.obj) else None for row in rows
        ]
        channels_bank_pos = [row.rownum for row in rows]

        model_support.sort_channels(channels, field)

        for chan, idx in zip(channels, channels_bank_pos, strict=True):
            if chan:
                chan.bank_pos = idx

        final_channels = [c for c in channels if c]

        self._change_manager.set_channel(*final_channels)
        self._change_manager.commit()
        self._update_chan_list()


def _bank_list_label(idx: int, bank_name: str, active: int) -> str:
    bname = consts.BANK_NAMES[idx]
    return (
        f"{bname}:  {bank_name:}  ({active})"
        if bank_name
        else f"{bname}  ({active})"
    )


def validate_bank_name(name: str | None) -> bool:
    if not name:
        return True

    try:
        validators.validate_name(name)
    except ValueError:
        return False

    return True

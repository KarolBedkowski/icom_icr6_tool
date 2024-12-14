# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from tkinter import messagebox, ttk

from . import (
    consts,
    expimp,
    fixers,
    gui_bankchanlist,
    gui_model,
    model,
    validators,
)
from .change_manager import ChangeManeger
from .gui_widgets import (
    new_checkbox,
    new_entry,
)
from .radio_memory import RadioMemory

_LOG = logging.getLogger(__name__)


class BanksPage(tk.Frame):
    def __init__(self, parent: tk.Widget, cm: ChangeManeger) -> None:
        super().__init__(parent)
        self._parent = parent
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._bank_name = tk.StringVar()
        self._bank_link = gui_model.BoolVar()
        self._change_manager = cm
        self._last_selected_bank = 0
        self.__select_after_refresh: int | None = None

        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        banks = self._banks_list = tk.Listbox(pw, selectmode=tk.SINGLE)

        banks.bind("<<ListboxSelect>>", self.__on_bank_select)
        pw.add(banks, weight=0)

        frame = tk.Frame(pw)
        self.__create_bank_fields(frame)
        self.__create_chan_list(frame)
        pw.add(frame, weight=1)

        pw.pack(expand=True, fill=tk.BOTH, side=tk.TOP, padx=12, pady=12)

        self.__update_banks_list()

    def update_tab(self) -> None:
        # hide canceller in global models
        self._chan_list.set_hide_canceller(
            hide=not self._radio_memory.is_usa_model()
        )

        self.__update_banks_list()
        self._banks_list.selection_set(self._last_selected_bank)
        self.__update_chan_list()

    def select(self, bank: int, bank_pos: int | None = None) -> None:
        self._banks_list.selection_set(bank)
        self.__select_after_refresh = bank_pos

    @property
    def _radio_memory(self) -> RadioMemory:
        return self._change_manager.rm

    def __create_bank_fields(self, frame: tk.Frame) -> None:
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
        self._btn_update = ttk.Button(
            fields, text="Update", command=self.__on_bank_update
        )
        self._btn_update.grid(row=0, column=3, sticky=tk.E, padx=6)

        fields.pack(side=tk.TOP, fill=tk.X, ipady=6)

    def __create_chan_list(self, frame: tk.Frame) -> None:
        self._chan_list = gui_bankchanlist.ChannelsList(frame)
        self._chan_list.pack(side=tk.TOP, expand=True, fill=tk.BOTH, ipady=6)

        self._chan_list.on_record_selected = self.__on_channel_select  # type: ignore
        self._chan_list.on_record_update = self.__on_channel_update  # type: ignore
        self._chan_list.sheet.bind("<Control-c>", self.__on_channel_copy)
        self._chan_list.sheet.bind("<Control-v>", self.__on_channel_paste)

        bframe = tk.Frame(frame)
        self._btn_sort = ttk.Button(
            bframe,
            text="Sort...",
            command=self.__on_btn_sort,
            state="disabled",
        )
        self._btn_sort.pack(side=tk.LEFT)

        bframe.pack(side=tk.BOTTOM, fill=tk.X, ipady=6)

    def __on_bank_select(self, _event: tk.Event) -> None:  # type: ignore
        self._chan_list.reset()
        self.__update_chan_list()

    def __update_banks_list(self) -> None:
        selected_bank = self.selected_bank

        banks = self._banks_list

        banks.delete(0, banks.size())
        for bank, bname in zip(
            self._radio_memory.banks, consts.BANK_NAMES, strict=True
        ):
            name = f"{bname}: {bank.name}" if bank.name else bname
            banks.insert(tk.END, name)

        if selected_bank is not None:
            banks.selection_set(selected_bank)
        else:
            self._field_bank_name["state"] = "disabled"
            self._field_bank_link["state"] = "disabled"
            self._btn_update["state"] = "disabled"
            self._chan_list.set_data([])
            self._bank_name.set("")

    def __update_chan_list(self, _event: tk.Event | None = None) -> None:  # type: ignore
        selected_bank = self.selected_bank
        if selected_bank is None:
            return

        self._chan_list.set_bank(selected_bank)
        self._last_selected_bank = selected_bank

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
        self._btn_update["state"] = "normal"
        self._show_stats()

        if self.__select_after_refresh is not None:
            self._chan_list.selection_set([self.__select_after_refresh])
            self.__select_after_refresh = None

    def _show_stats(self) -> None:
        active = sum(
            bool(r and (c := r.channel) and not c.hide_channel)
            for r in self._chan_list.data
        )
        self._parent.set_status(f"Active channels in bank: {active}")  # type: ignore

    @property
    def selected_bank(self) -> int | None:
        """selected bank"""

        if sel_bank := self._banks_list.curselection():  # type: ignore
            return int(sel_bank[0])

        return None

    def __on_bank_update(self) -> None:
        selected_bank = self.selected_bank
        if selected_bank is None:
            return

        bank = self._radio_memory.banks[selected_bank].clone()
        bank.name = self._bank_name.get().strip()[:6]
        self._change_manager.set_bank(bank)

        bl = self._radio_memory.bank_links.clone()
        bl[selected_bank] = self._bank_link.get_raw()
        self._change_manager.set_bank_links(bl)

        self._change_manager.commit()
        self.__update_banks_list()

    def __on_channel_select(self, rows: list[gui_bankchanlist.BLRow]) -> None:
        if len(rows) > 1:
            self._btn_sort["state"] = "normal"

    def __on_channel_update(
        self, action: str, rows: ty.Collection[gui_bankchanlist.BLRow]
    ) -> None:
        match action:
            case "delete":
                self.__do_delete_channels(rows)

            case "update":
                self.__do_update_channels(rows)

            case "move":
                self.__do_move_channels(rows)

    def __do_delete_channels(
        self, rows: ty.Collection[gui_bankchanlist.BLRow]
    ) -> None:
        chan: model.Channel | None
        if not messagebox.askyesno(
            "Delete channel",
            "Delete channel configuration from bank?",
            icon=messagebox.WARNING,
        ):
            return

        channels = []
        for rec in rows:
            if chan := rec.channel:
                _LOG.debug("__do_delete_channels: row=%r, chan=%r", rec, chan)
                chan = chan.clone()
                chan.clear_bank()
                channels.append(chan)

        self._change_manager.set_channel(*channels)
        self._change_manager.commit()
        self.__update_chan_list()

    def __do_update_channels(
        self, rows: ty.Collection[gui_bankchanlist.BLRow]
    ) -> None:
        chan: model.Channel | None

        selected_bank = self.selected_bank
        if selected_bank is None:
            return

        channels = []
        for rec in rows:
            _LOG.debug(
                "__do_update_channels: row=%r, chan=%r",
                rec,
                rec.channel,
            )

            if rec.new_channel is not None:  # change channel in bankpos
                if old_chan := rec.channel:
                    # clear old chan
                    old_chan.clear_bank()
                    channels.append(old_chan)

                # add chan to bank
                chan = self._radio_memory.channels[rec.new_channel]

            elif rec.new_freq:  # empty pos, entered freq
                chan = self._radio_memory.find_first_hidden_channel()
                if not chan:
                    continue

                chan.freq = rec.new_freq
                chan.mode = consts.default_mode_for_freq(chan.freq)

            elif rec.channel:  # edit existing channel
                chan = rec.channel

            else:
                # no chan = deleted  # TODO: change
                self._change_manager.clear_bank_pos(selected_bank, rec.rownum)
                continue

            chan.bank = selected_bank
            chan.bank_pos = rec.rownum

            # if new channel - make it visible
            if chan.hide_channel or not chan.freq:
                chan.freq = fixers.fix_frequency(chan.freq)
                band = self._change_manager.rm.get_band_for_freq(chan.freq)
                chan.load_defaults_from_band(band)
                chan.hide_channel = False

            channels.append(chan)

        self._change_manager.set_channel(*channels)
        self._change_manager.commit()
        self.__update_chan_list()

    def __do_move_channels(
        self, rows: ty.Collection[gui_bankchanlist.BLRow]
    ) -> None:
        channels = []
        for rec in rows:
            if not rec.channel:
                continue

            _LOG.debug("__do_move_channels: %r -> %d", rec.channel, rec.rownum)
            chan = rec.channel.clone()
            chan.bank_pos = rec.rownum
            channels.append(chan)

        if channels:
            self._change_manager.set_channel(*channels)
            self._change_manager.commit()
            self.__update_chan_list()

    def __on_channel_copy(self, _event: tk.Event) -> None:  # type: ignore
        selected = self._chan_list.sheet.get_currently_selected()
        if not selected:
            return

        res = None

        if selected.type_ == "rows":
            if rows := self._chan_list.selected_rows_data():
                channels = (chan for row in rows if (chan := row.channel))
                res = expimp.export_channel_str(channels)

        elif selected.type_ == "cells" and (
            data := self._chan_list.selected_data()
        ):
            res = expimp.export_table_as_string(data).strip()

        if res:
            gui_model.Clipboard.instance().put(res)

    def __on_channel_paste(self, _event: tk.Event) -> None:  # type: ignore
        selected_bank = self.selected_bank
        if selected_bank is None:
            return

        sel = self._chan_list.selection()
        if not sel:
            return

        clip = gui_model.Clipboard.instance()
        data = ty.cast(str, clip.get())
        try:
            # try import whole channels
            self.__on_channel_paste_channels(selected_bank, sel, data)
        except ValueError:
            # try import as plain data
            self.__on_channel_paste_simple(data)
        except Exception:
            _LOG.exception("__on_channel_paste error")

    def __on_channel_paste_channels(
        self, selected_bank: int, sel_pos: tuple[int, ...], data: str
    ) -> None:
        try:
            rows = list(expimp.import_channels_str(data))
        except ValueError:
            raise
        except Exception:
            _LOG.exception("import from clipboard error")
            return

        bank_channels = self._radio_memory.get_bank_channels(selected_bank)

        # special case - when in clipboard is one record and selected  many-
        # duplicate
        if len(sel_pos) > 1 and len(rows) == 1:
            row = rows[0]
            for spos in sel_pos:
                if not self.__paste_channel(
                    row, spos, selected_bank, bank_channels
                ):
                    break

        else:
            for pos, row in enumerate(rows, sel_pos[0]):
                if not self.__paste_channel(
                    row, pos, selected_bank, bank_channels
                ):
                    break

                if pos % 100 == 99:  # noqa: PLR2004
                    break

        self._change_manager.commit()
        self.__update_chan_list()

    def __on_channel_paste_simple(self, data: str) -> None:
        try:
            rows = expimp.import_str_as_table(data)
        except ValueError:
            raise
        except Exception:
            _LOG.exception("simple import from clipboard error")
            raise

        self._chan_list.paste(rows)

    def __paste_channel(
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
                _LOG.warn("no hidden channel found")
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

    def __on_btn_sort(self) -> None:
        rows = self._chan_list.selected_rows_data()
        if len(rows) <= 1:
            return

        popup_menu = tk.Menu(self, tearoff=0)
        popup_menu.add_command(
            label="Sort by frequency", command=lambda: self.__do_sort("freq")
        )

        popup_menu.add_command(
            label="Sort by name", command=lambda: self.__do_sort("name")
        )
        popup_menu.add_command(
            label="Sort by name (empty first)",
            command=lambda: self.__do_sort("name2"),
        )
        popup_menu.add_command(
            label="Sort by channel number",
            command=lambda: self.__do_sort("channel"),
        )
        popup_menu.add_separator()
        popup_menu.add_command(
            label="Pack", command=lambda: self.__do_sort("pack")
        )
        try:
            btn = self._btn_sort
            popup_menu.tk_popup(btn.winfo_rootx(), btn.winfo_rooty())
        finally:
            popup_menu.grab_release()

    def __do_sort(self, field: str) -> None:  # noqa: C901
        rows = self._chan_list.selected_rows_data()
        if len(rows) <= 1:
            return

        channels = [row.channel for row in rows]
        channels_bank_pos = [row.rownum for row in rows]

        sfunc: ty.Callable[[model.Channel], str | int]

        match field:
            case "name":

                def sfunc(chan: model.Channel | None) -> str:
                    return chan.name or "\xff" if chan else "\xff"

            case "name2":

                def sfunc(chan: model.Channel | None) -> str:
                    return chan.name if chan else ""

            case "freq":

                def sfunc(chan: model.Channel | None) -> int:
                    return chan.freq if chan and not chan.hide_channel else 0

            case "pack":

                def sfunc(chan: model.Channel | None) -> int:
                    return 0 if chan else 1

            case "channel":

                def sfunc(chan: model.Channel | None) -> int:
                    return chan.number if chan else 1400

            case _:
                raise ValueError

        channels.sort(key=sfunc)

        for chan, idx in zip(channels, channels_bank_pos, strict=True):
            if chan:
                chan.bank_pos = idx

        self._change_manager.set_channel(*channels)
        self._change_manager.commit()
        self.__update_chan_list()


def validate_bank_name(name: str | None) -> bool:
    if not name:
        return True

    try:
        validators.validate_name(name)
    except ValueError:
        return False

    return True

# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from operator import attrgetter
from tkinter import messagebox, ttk

from . import consts, expimp, gui_chanlist, gui_model, model

_LOG = logging.getLogger(__name__)


class ChannelsPage(tk.Frame):
    _chan_list: gui_chanlist.ChannelsList

    def __init__(
        self, parent: tk.Widget, radio_memory: model.RadioMemory
    ) -> None:
        super().__init__(parent)
        self._parent = parent
        self._radio_memory = radio_memory
        self._last_selected_group = 0
        self._last_selected_chan: tuple[int, ...] = ()
        self.__need_full_refresh = False

        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self._groups_list = tk.Listbox(pw, selectmode=tk.SINGLE)
        self._groups_list.insert(tk.END, *gui_model.CHANNEL_RANGES)
        self._groups_list.bind("<<ListboxSelect>>", self.__update_chan_list)
        pw.add(self._groups_list, weight=0)

        frame = tk.Frame(pw)
        self._create_channel_list(frame)
        pw.add(frame, weight=1)

        pw.pack(expand=True, fill=tk.BOTH, side=tk.TOP, padx=12, pady=12)

    def update_tab(self, radio_memory: model.RadioMemory) -> None:
        self._radio_memory = radio_memory

        # hide canceller in global models
        self._chan_list.set_hide_canceller(
            hide=not radio_memory.is_usa_model()
        )

        self._groups_list.selection_set(self._last_selected_group)
        self.__update_chan_list()
        self._chan_list.selection_set(self._last_selected_chan)

    def _create_channel_list(self, frame: tk.Frame) -> None:
        self._chan_list = gui_chanlist.ChannelsList(frame)
        self._chan_list.on_record_update = self.__on_channel_update
        self._chan_list.on_record_selected = self.__on_channel_select
        self._chan_list.on_channel_bank_validate = self.__on_channel_bank_set
        self._chan_list.pack(side=tk.TOP, expand=True, fill=tk.BOTH, ipady=6)
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

    def __on_channel_update(
        self, action: str, rows: ty.Collection[gui_chanlist.Row]
    ) -> None:
        match action:
            case "delete":
                self.__do_delete_channels(rows)

            case "update":
                self.__do_update_channels(rows)

            case "move":
                self.__do_move_channels(rows)

    def __do_delete_channels(
        self, rows: ty.Collection[gui_chanlist.Row]
    ) -> None:
        if not messagebox.askyesno(
            "Delete channel",
            "Delete channel configuration?",
            icon=messagebox.WARNING,
        ):
            return

        for rec in rows:
            _LOG.debug("__do_delete_channels: %r", rec)
            if chan := rec.channel:
                chan.delete()
                self._radio_memory.set_channel(chan)

        self.__update_chan_list()

    def __do_update_channels(
        self, rows: ty.Collection[gui_chanlist.Row]
    ) -> None:
        for rec in rows:
            _LOG.debug("__do_update_channels: %r", rec)
            self._radio_memory.set_channel(rec.channel)

        if self.__need_full_refresh:
            self.__update_chan_list()
        else:
            self._show_stats()

    def __do_move_channels(
        self, rows: ty.Collection[gui_chanlist.Row]
    ) -> None:
        if sel := self._groups_list.curselection():  # type: ignore
            selected_range = sel[0]
        else:
            return

        range_start = selected_range * 100

        for rec in rows:
            channum = range_start + rec.rownum
            _LOG.debug("__do_move_channels: %r -> %d", rec, channum)
            rec.channel.number = channum
            self._radio_memory.set_channel(rec.channel)

        self.__update_chan_list()

    def __on_channel_select(self, rows: list[gui_chanlist.Row]) -> None:
        if len(rows) > 1:
            self._btn_sort["state"] = "normal"

        for rec in rows:
            _LOG.debug("chan selected: %r", rec.channel)

    def __update_chan_list(self, _event: tk.Event | None = None) -> None:  # type: ignore
        if sel := self._groups_list.curselection():  # type: ignore
            selected_range = sel[0]
        else:
            return

        self._last_selected_group = sel[0]

        range_start = selected_range * 100
        self._chan_list.set_data(
            [
                self._radio_memory.get_channel(idx)
                for idx in range(range_start, range_start + 100)
            ]
        )

        self._show_stats()
        self.__need_full_refresh = False

    def __on_channel_copy(self, _event: tk.Event) -> None:  # type: ignore
        rows = self._chan_list.selected_rows()
        if not rows:
            return

        channels = (chan for row in rows if (chan := row.channel))
        clip = gui_model.Clipboard.instance()
        clip.put(expimp.export_channel_str(channels))

    def __on_channel_paste(self, _event: tk.Event) -> None:  # type: ignore
        sel = self._chan_list.selection()
        if not sel:
            return

        clip = gui_model.Clipboard.instance()

        try:
            rows = list(expimp.import_channels_str(ty.cast(str, clip.get())))
        except Exception:
            _LOG.exception("import from clipboard error")
            return

        range_start = self._last_selected_group * 100

        # special case - when in clipboard is one record and selected  many-
        # duplicate
        if len(sel) > 1 and len(rows) == 1:
            row = rows[0]
            for spos in sel:
                if not self.__paste_channel(row, spos + range_start):
                    break

        else:
            start_num = sel[0] + range_start
            for chan_num, row in enumerate(rows, start_num):
                if not self.__paste_channel(row, chan_num):
                    break
                # stop on range boundary
                if chan_num % 100 == 99:  # noqa: PLR2004
                    break

        self.__update_chan_list()

    def __paste_channel(self, row: dict[str, object], chan_num: int) -> bool:
        _LOG.debug("__paste_channel chan_num=%d, row=%r", chan_num, row)
        chan = self._radio_memory.get_channel(chan_num).clone()
        # do not clean existing rows
        if not row.get("freq"):
            _LOG.debug("paste empty row to not empty")
            return True

        try:
            chan.from_record(row)
            chan.validate()
        except ValueError:
            _LOG.exception("import from clipboard error")
            _LOG.error("chan_num=%d, row=%r", chan_num, row)
            return False

        chan.hide_channel = False
        # do not set bank on paste
        chan.bank = consts.BANK_NOT_SET
        chan.bank_pos = 0
        self._radio_memory.set_channel(chan)

        return True

    def _show_stats(self) -> None:
        active = sum(
            bool(r and (c := r.channel) and not c.hide_channel)
            for r in self._chan_list.data
        )
        self._parent.set_status(f"Active channels: {active}")  # type: ignore

    def __on_channel_bank_set(
        self,
        bank: int | str,
        channum: int,
        bank_pos: int,
        *,
        try_set_free_slot: bool = False,
    ) -> int:
        if bank in (consts.BANK_NOT_SET, ""):
            return bank_pos

        if isinstance(bank, str):
            bank = consts.BANK_NAMES.index(bank)

        bank_channels = self._radio_memory.get_bank_channels(bank)
        dst_bank_pos = bank_channels[bank_pos]
        if dst_bank_pos == channum:
            # no changes
            return bank_pos

        # is position empty
        if dst_bank_pos is None:
            return bank_pos

        # selected bank pos is occupied by other chan

        if try_set_free_slot:
            # find unused next slot
            pos = bank_channels.find_free_slot(bank_pos)
            if pos is None:
                # not found next, search from beginning
                # find first unused slot
                pos = bank_channels.find_free_slot()

            if pos is not None:
                return pos

        # not found unused slot - replace, require update other rows
        # this may create duplicates !!!! FIXME: mark duplicates
        self.__need_full_refresh = True
        return bank_pos

    def __on_btn_sort(self) -> None:
        rows = self._chan_list.selected_rows()
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
        rows = self._chan_list.selected_rows()
        if len(rows) <= 1:
            return

        channels = [chan for row in rows if (chan := row.channel)]
        channels_ids = [chan.number for chan in channels]

        sfunc: ty.Callable[[model.Channel], str | int]

        match field:
            case "name":

                def sfunc(chan: model.Channel) -> str:
                    return chan.name or "\xff"

            case "name2":
                sfunc = attrgetter(field)

            case "freq":

                def sfunc(chan: model.Channel) -> int:
                    return 0 if chan.hide_channel else chan.freq

            case "pack":

                def sfunc(chan: model.Channel) -> int:
                    return 1 if (chan.hide_channel or not chan.freq) else 0

            case _:
                raise ValueError

        channels.sort(key=sfunc)

        for chan, idx in zip(channels, channels_ids, strict=True):
            chan.number = idx
            self._radio_memory.set_channel(chan)

        self.__update_chan_list()

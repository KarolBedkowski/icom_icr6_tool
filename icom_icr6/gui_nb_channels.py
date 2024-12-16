# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from contextlib import suppress
from tkinter import messagebox, ttk

from . import (
    consts,
    expimp,
    fixers,
    gui_chanlist,
    gui_model,
    model_support,
)
from .change_manager import ChangeManeger
from .radio_memory import RadioMemory

_LOG = logging.getLogger(__name__)


class ChannelsPage(tk.Frame):
    _chan_list: gui_chanlist.ChannelsList

    def __init__(self, parent: tk.Widget, cm: ChangeManeger) -> None:
        super().__init__(parent)
        self._parent = parent
        self._change_manager = cm
        self._last_selected_group = 0
        self._last_selected_chan: tuple[int, ...] = ()
        self.__need_full_refresh = False
        self.__select_after_refresh: int | None = None

        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self._groups_list = tk.Listbox(pw, selectmode=tk.SINGLE, width=10)
        self._groups_list.insert(tk.END, *gui_model.CHANNEL_RANGES)
        self._groups_list.bind("<<ListboxSelect>>", self.__on_group_select)
        pw.add(self._groups_list, weight=0)

        frame = tk.Frame(pw)
        self._create_channel_list(frame)
        pw.add(frame, weight=1)

        pw.pack(expand=True, fill=tk.BOTH, side=tk.TOP, padx=12, pady=12)

    def update_tab(self, channel_number: int | None = None) -> None:
        # hide canceller in global models
        self._chan_list.set_hide_canceller(
            hide=not self._radio_memory.is_usa_model()
        )

        if channel_number is not None:
            group, chanpos = divmod(channel_number, 100)
            self._last_selected_chan = (group,)
            self.__select_after_refresh = chanpos

        self._groups_list.selection_set(self._last_selected_group)
        self.__update_chan_list()
        self._chan_list.selection_set(self._last_selected_chan)

    def select(self, channel_number: int) -> None:
        group, chanpos = divmod(channel_number, 100)
        self.__select_after_refresh = chanpos

        self._groups_list.selection_set(group)

    @property
    def _radio_memory(self) -> RadioMemory:
        return self._change_manager.rm

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

        self._btn_fill = ttk.Button(
            bframe,
            text="Fill values...",
            command=self.__on_btn_fill,
            state="disabled",
        )
        self._btn_fill.pack(side=tk.LEFT)

        bframe.pack(side=tk.BOTTOM, fill=tk.X, ipady=6)

    def __on_group_select(self, _event: tk.Event) -> None:  # type: ignore
        self._chan_list.reset(scroll_top=True)
        self.__update_chan_list()

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

        channels = []
        for rec in rows:
            _LOG.debug("__do_delete_channels: %r", rec)
            if chan := rec.channel:
                chan = chan.clone()
                chan.delete()
                channels.append(chan)

        self._change_manager.set_channel(*channels)
        self._change_manager.commit()
        self.__update_chan_list()

    def __do_update_channels(
        self, rows: ty.Collection[gui_chanlist.Row]
    ) -> None:
        channels = []
        for rec in rows:
            _LOG.debug("__do_update_channels: %r", rec)
            rec.updated = False
            chan = rec.channel

            if rec.new_freq:
                chan = chan.clone()
                band = self._change_manager.rm.get_band_for_freq(rec.new_freq)
                chan.load_defaults_from_band(band)
                chan.freq = rec.new_freq
                chan.hide_channel = False
                self.__need_full_refresh = True

            channels.append(chan)

        self.__need_full_refresh |= self._change_manager.set_channel(*channels)
        self._change_manager.commit()
        if self.__need_full_refresh:
            self.__update_chan_list()
        else:
            self._show_stats()

    @property
    def _selected_range(self) -> int | None:
        if sel := self._groups_list.curselection():  # type: ignore
            return sel[0]  # type: ignore

        return None

    def __do_move_channels(
        self, rows: ty.Collection[gui_chanlist.Row]
    ) -> None:
        selected_range = self._selected_range
        if selected_range is None:
            return

        range_start = selected_range * 100
        channels = []

        for rec in rows:
            channum = range_start + rec.rownum
            _LOG.debug("__do_move_channels: %r -> %d", rec, channum)
            rec.channel.number = channum
            channels.append(rec.channel)

        self._change_manager.set_channel(*channels)
        self._change_manager.commit()
        self.__update_chan_list()

    def __on_channel_select(self, rows: list[gui_chanlist.Row]) -> None:
        if len(rows) > 1:
            self._btn_sort["state"] = "normal"
            self._btn_fill["state"] = "normal"

        for rec in rows:
            _LOG.debug("chan selected: %r", rec.channel)

    def __update_chan_list(self, _event: tk.Event | None = None) -> None:  # type: ignore
        selected_range = self._selected_range
        if selected_range is None:
            return

        self._last_selected_group = selected_range

        range_start = selected_range * 100
        self._chan_list.set_data(
            self._radio_memory.channels[range_start : range_start + 100]
        )

        self._show_stats()
        self.__need_full_refresh = False

        if self.__select_after_refresh is not None:
            sel = self.__select_after_refresh
            self.after(100, lambda: self._chan_list.selection_set([sel]))
            self.__select_after_refresh = None

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
        sel = self._chan_list.selection()
        if not sel:
            return

        clip = gui_model.Clipboard.instance()
        data = ty.cast(str, clip.get())
        try:
            # try import whole channels
            self.__on_channel_paste_channels(sel, data)
        except ValueError:
            # try import as plain data
            self.__on_channel_paste_simple(data)
        except Exception:
            _LOG.exception("__on_channel_paste error")
        else:
            self._change_manager.commit()
            self.__update_chan_list()

    def __on_channel_paste_channels(
        self, sel: tuple[int, ...], data: str
    ) -> None:
        try:
            rows = list(expimp.import_channels_str(data))
        except ValueError:
            raise
        except Exception:
            _LOG.exception("import from clipboard error")
            raise

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

    def __on_channel_paste_simple(self, data: str) -> None:
        try:
            rows = expimp.import_str_as_table(data)
        except ValueError:
            raise
        except Exception:
            _LOG.exception("simple import from clipboard error")
            raise

        if not rows:
            return

        self._chan_list.paste(rows)

    def __paste_channel(self, row: dict[str, object], chan_num: int) -> bool:
        _LOG.debug("__paste_channel chan_num=%d, row=%r", chan_num, row)
        chan = self._radio_memory.channels[chan_num].clone()
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
        self._change_manager.set_channel(chan)

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
        _LOG.debug("__on_channel_bank_set %r, %r, %r", bank, channum, bank_pos)
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
        # this may create duplicates  but this should be cleaned on channel
        # save
        self.__need_full_refresh = True
        return bank_pos

    def __on_btn_sort(self) -> None:
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

        channels = [chan.clone() for row in rows if (chan := row.channel)]
        channels_ids = [chan.number for chan in channels]

        model_support.sort_channels(channels, field)

        for chan, idx in zip(channels, channels_ids, strict=True):
            chan.number = idx

        self._change_manager.set_channel(*channels)
        self._change_manager.commit()
        self.__update_chan_list()

    def __on_btn_fill(self) -> None:
        rows = self._chan_list.selected_rows_data()
        if len(rows) <= 1:
            return

        popup_menu = tk.Menu(self, tearoff=0)
        popup_menu.add_command(
            label="Copy first row to following", command=self.__do_fill_down
        )

        popup_menu.add_command(
            label="Increment freq by TS", command=self.__do_fill_freq
        )
        try:
            btn = self._btn_fill
            popup_menu.tk_popup(btn.winfo_rootx(), btn.winfo_rooty())
        finally:
            popup_menu.grab_release()

    def __do_fill_down(self) -> None:
        """Copy value from first selected cell down"""
        sel_rows = self._chan_list.selected_rows()
        if len(sel_rows) <= 1:
            return

        sheet = self._chan_list.sheet

        # visible cols
        sel_cols = self._chan_list.selected_columns()
        if not sel_cols:
            sel_cols = self._chan_list.visible_cols()

        min_col, max_col = sel_cols[0], sel_cols[-1] + 1
        first_row = sel_rows[0]
        data = sheet[(first_row, min_col), (first_row + 1, max_col)].data

        with suppress(ValueError):
            # remove bano_pos if is on list
            idx = sel_cols.index(self._chan_list.colmap["bank_pos"])
            data[idx] = None

        for row in sel_rows[1:]:
            sheet.span((row, min_col), emit_event=True).data = data

    def __do_fill_freq(self) -> None:
        """Copy freq from first row increased by ts"""
        sel_rows = self._chan_list.selected_rows()
        if len(sel_rows) <= 1:
            return

        sheet = self._chan_list.sheet
        chan = sheet.data[sel_rows[0]].channel
        if not chan or not chan.freq:
            return

        start_freq = chan.freq
        ts = consts.STEPS_KHZ[chan.tuning_step]

        self._chan_list.set_data_rows(
            1,
            (
                (row, [fixers.fix_frequency(int(start_freq + ts * idx))])
                for idx, row in enumerate(sel_rows[1:], 1)
            ),
        )

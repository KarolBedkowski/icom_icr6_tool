# Copyright © 2024-2025 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from contextlib import suppress
from tkinter import messagebox, ttk

from icom_icr6 import consts, expimp, fixers, model_support
from icom_icr6.change_manager import ChangeManeger
from icom_icr6.radio_memory import RadioMemory

from . import channels_list, gui_model

_LOG = logging.getLogger(__name__)


class ChannelsPage(tk.Frame):
    _chan_list: channels_list.ChannelsList2

    def __init__(self, parent: tk.Widget, cm: ChangeManeger) -> None:
        super().__init__(parent)
        self._parent = parent
        self._change_manager = cm
        self._need_full_refresh = False
        self._in_paste = False
        self._last_selected_group = 0
        # keep selection per group
        self._last_selected_pos = [0] * len(gui_model.CHANNEL_RANGES)
        # labels with stats
        self._groups_labels: list[str] = []
        self._groups = tk.StringVar(value=self._groups_labels)  # type: ignore
        self._update_groups_list()

        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self._groups_list = tk.Listbox(
            pw, selectmode=tk.SINGLE, width=10, listvariable=self._groups
        )
        self._groups_list.bind("<<ListboxSelect>>", self._on_group_select)
        pw.add(self._groups_list, weight=0)

        frame = tk.Frame(pw)
        self._create_channel_list(frame)
        self._chan_list.set_radio_memory(cm.rm)
        pw.add(frame, weight=1)

        pw.pack(expand=True, fill=tk.BOTH, side=tk.TOP, padx=12, pady=12)

    def update_tab(self, channel_number: int | None = None) -> None:
        # hide canceller in global models
        self._chan_list.set_radio_memory(self._change_manager.rm)
        self._update_groups_list()

        if channel_number is None:
            channel_number = (
                self._last_selected_group * 100
                + self._last_selected_pos[self._last_selected_group]
            )

        self.select(channel_number, force=True)

    def select(self, channel_number: int, *, force: bool = False) -> None:
        group, chanpos = divmod(channel_number, 100)

        current_sel_group = self._selected_group

        self._last_selected_pos[group] = chanpos
        self._last_selected_group = group

        if group == current_sel_group and not force:
            self._chan_list.selection_set([chanpos])
            return

        self._groups_list.selection_clear(0, 13)
        self._groups_list.selection_set(group)
        self._update_chan_list(select=chanpos)

    def reset(self) -> None:
        self._chan_list.set_radio_memory(self._change_manager.rm)
        self._last_selected_group = 0
        self._last_selected_pos = [0] * len(gui_model.CHANNEL_RANGES)
        self._groups_list.selection_set(0)
        self._update_chan_list()
        self._update_groups_list()

    @property
    def _radio_memory(self) -> RadioMemory:
        return self._change_manager.rm

    def _create_channel_list(self, frame: tk.Frame) -> None:
        self._chan_list = channels_list.ChannelsList2(
            frame, self._change_manager.rm
        )
        self._chan_list.on_record_update = self._on_channel_update
        self._chan_list.on_record_selected = self._on_channel_select
        self._chan_list.on_channel_bank_validate = self._on_channel_bank_set
        self._chan_list.pack(side=tk.TOP, expand=True, fill=tk.BOTH, pady=6)
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

        self._btn_fill = ttk.Button(
            bframe,
            text="Fill values...",
            command=self._on_btn_fill,
            state="disabled",
        )
        self._btn_fill.pack(side=tk.LEFT)

        bframe.pack(side=tk.BOTTOM, fill=tk.X)

    def _on_group_select(self, _event: tk.Event) -> None:  # type: ignore
        sel_group = self._selected_group
        if sel_group is None:
            return

        self._last_selected_group = sel_group
        self._chan_list.reset(scroll_top=True)
        self._update_chan_list(select=self._last_selected_pos[sel_group])

    def _on_channel_update(
        self, action: str, rows: ty.Collection[channels_list.RowType]
    ) -> None:
        match action:
            case "delete":
                self._do_delete_channels(rows)

            case "update":
                self._do_update_channels(rows)

            case "move":
                self._do_move_channels(rows)

    def _do_delete_channels(
        self, rows: ty.Collection[channels_list.RowType]
    ) -> None:
        if not messagebox.askyesno(
            "Delete channel",
            "Delete channel configuration?",
            icon=messagebox.WARNING,
        ):
            return

        channels = []
        for row in rows:
            _LOG.debug("_do_delete_channels: %r", row)
            if chan := row.obj:
                chan = chan.clone()
                chan.delete()
                channels.append(chan)

        self._change_manager.set_channel(*channels)
        self._change_manager.commit()

        for chan in channels:
            self._chan_list.update_data(chan.number % 100, chan)

    def _do_update_channels(
        self, rows: ty.Collection[channels_list.RowType]
    ) -> None:
        channels = []
        for row in rows:
            _LOG.debug("_do_update_channels: %r", row)
            if not row.changes:
                _LOG.warning("_do_update_channels: no changes: %r", row)
                continue

            chan = row.obj
            assert chan is not None
            chan = chan.clone()

            # chan is hidden and freq is given - load defaults for this freq
            if chan.hide_channel and (freq := row.changes.get("freq")):
                assert isinstance(freq, int)
                band = self._change_manager.rm.get_band_for_freq(freq)
                chan.load_defaults_from_band(band)
                chan.tuning_step = fixers.fix_tuning_step(
                    chan.freq, chan.tuning_step
                )

            # update channel from changes and unhide if freq is valid
            chan.from_record(row.changes)
            chan.hide_channel = chan.freq == 0
            channels.append(chan)

        # other channels may be changed (replace bank pos)
        self._need_full_refresh |= self._change_manager.set_channel(*channels)

        # to not commit changes when in paste; commit is at the end
        if self._in_paste:
            return

        self._change_manager.commit()
        if self._need_full_refresh:
            self._update_chan_list()
        else:
            # update only changed channels
            for chan in channels:
                self._chan_list.update_data(chan.number % 100, chan)

            self._show_stats()

    @property
    def _selected_group(self) -> int | None:
        if sel := self._groups_list.curselection():
            return sel[0]  # type: ignore

        return None

    def _update_groups_list(self) -> None:
        self._groups_labels = groups = []
        for group in range(13):
            active = sum(
                1
                for c in self._change_manager.rm.get_active_channels_in_group(
                    group
                )
            )
            groups.append(f"{group:>2}  ({active})")

        self._groups.set(groups)  # type: ignore

    def _do_move_channels(
        self, rows: ty.Collection[channels_list.RowType]
    ) -> None:
        sel_group = self._selected_group
        if sel_group is None:
            return

        range_start = sel_group * 100
        channels = []

        for row in rows:
            assert row.obj
            # new position in in row.rownum
            channum = range_start + row.rownum
            _LOG.debug("_do_move_channels: %r -> %d", row, channum)
            chan = row.obj.clone()
            chan.number = channum
            channels.append(chan)

        self._change_manager.set_channel(*channels)
        self._change_manager.commit()

        for chan in channels:
            self._chan_list.update_data(chan.number % 100, chan)

    def _on_channel_select(self, rows: list[channels_list.RowType]) -> None:
        # change buttons state
        btn_state = "normal" if len(rows) > 1 else "disabled"
        self._btn_sort["state"] = btn_state
        self._btn_fill["state"] = btn_state

        # remember selected position in group
        chan = rows[0].obj
        assert chan is not None
        num = chan.number
        self._last_selected_group, pos = divmod(num, 100)
        self._last_selected_pos[self._last_selected_group] = pos

        if _LOG.isEnabledFor(logging.DEBUG):
            for row in rows:
                _LOG.debug("chan selected: %r", row.obj)

    def _update_chan_list(
        self,
        _event: tk.Event | None = None,  # type: ignore
        *,
        select: int | None = None,
    ) -> None:
        sel_group = self._last_selected_group
        range_start = sel_group * 100
        self._chan_list.set_data(
            self._radio_memory.channels[range_start : range_start + 100]
        )

        self._show_stats()
        self._need_full_refresh = False

        if select is not None:
            self.update_idletasks()
            self.after(10, lambda: self._chan_list.selection_set([select]))

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
        sel = self._chan_list.selected_rows()
        if not sel:
            return

        self._in_paste = True

        clip = gui_model.Clipboard.instance()
        data = ty.cast(str, clip.get())
        try:
            # try import whole channels
            if not self._on_channel_paste_channels(sel, data):
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

        finally:
            self._in_paste = False

    def _on_channel_paste_channels(
        self, sel: tuple[int, ...], data: str
    ) -> bool:
        """Try paste data in csv format. Return True on success."""
        if (sel_group := self._selected_group) is not None:
            range_start = sel_group * 100
        else:
            return False

        try:
            rows = list(expimp.import_channels_str(data))
        except ValueError:
            # data in invalid format
            return False

        # special case - when in clipboard is one record and selected  many-
        # duplicate
        if len(sel) > 1 and len(rows) == 1:
            row = rows[0]
            for spos in sel:
                if not self._paste_channel(row, spos + range_start):
                    break

        else:
            start_num = sel[0] + range_start
            for chan_num, row in enumerate(rows, start_num):
                if not self._paste_channel(row, chan_num):
                    break

                # stop on range boundary
                if chan_num % 100 == 99:  # noqa: PLR2004
                    break

        return True

    def _on_channel_paste_simple(self, data: str) -> None:
        """Paste simple data into tksheet.
        Raise on invalid data."""
        if rows := expimp.import_str_as_table(data):
            self._chan_list.paste(rows)

    def _paste_channel(self, row: dict[str, object], chan_num: int) -> bool:
        _LOG.debug("_paste_channel chan_num=%d, row=%r", chan_num, row)
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

        chan.hide_channel = chan.freq != 0
        # do not set bank on paste
        chan.bank = consts.BANK_NOT_SET
        chan.bank_pos = 0
        self._change_manager.set_channel(chan)

        return True

    def _show_stats(self) -> None:
        group = self._last_selected_group
        rm = self._change_manager.rm

        active = sum(1 for c in rm.get_active_channels_in_group(group))
        in_banks = sum(
            c.bank != consts.BANK_NOT_SET
            for c in rm.get_active_channels_in_group(group)
        )

        self._parent.set_status(  # type: ignore
            f"Active channels: {active}; in banks: {in_banks}"
        )

        # update group list stats
        self._groups_labels[group] = f"{group:>2}  ({active})"
        self._groups.set(self._groups_labels)  # type: ignore

    def _on_channel_bank_set(
        self,
        bank: int | str,
        channum: int,
        bank_pos: int,
        *,
        try_set_free_slot: bool = False,
    ) -> int | None:
        _LOG.debug("_on_channel_bank_set %r, %r, %r", bank, channum, bank_pos)
        if bank in (consts.BANK_NOT_SET, ""):
            return bank_pos

        # if bank name, map it to index
        if isinstance(bank, str):
            bank = consts.BANK_NAMES.index(bank[0])

        bank_channels = self._radio_memory.get_bank_channels(bank)

        # check current channel position in bank
        dst_bank_pos = bank_channels[bank_pos]
        if dst_bank_pos == channum:
            # no changes
            return bank_pos

        # is position empty
        if dst_bank_pos is None:
            return bank_pos

        # selected bank pos is occupied by other channel

        if try_set_free_slot:
            # find unused next slot
            pos = bank_channels.find_free_slot(bank_pos)
            if pos is None:
                # not found next, search from beginning
                # find first unused slot
                pos = bank_channels.find_free_slot()

            if pos is None:
                messagebox.showerror(
                    "Set channel bank",
                    "Not found free position in bank "
                    f"{consts.BANK_NAMES[bank]} for this channel.",
                )

            return pos

        # not found unused slot - replace, require update other rows
        # this may create duplicates  but this should be cleaned on channel
        # save
        self._need_full_refresh = True
        return bank_pos

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

        channels = [chan.clone() for row in rows if (chan := row.obj)]
        channels_ids = [chan.number for chan in channels]

        model_support.sort_channels(channels, field)

        for chan, idx in zip(channels, channels_ids, strict=True):
            chan.number = idx

        self._change_manager.set_channel(*channels)
        self._change_manager.commit()
        self._update_chan_list()

    def _on_btn_fill(self) -> None:
        rows = self._chan_list.selected_rows_data()
        if len(rows) <= 1:
            return

        popup_menu = tk.Menu(self, tearoff=0)
        popup_menu.add_command(
            label="Copy first row to following", command=self._do_fill_down
        )

        popup_menu.add_command(
            label="Increment freq by TS", command=self._do_fill_freq
        )
        try:
            btn = self._btn_fill
            popup_menu.tk_popup(btn.winfo_rootx(), btn.winfo_rooty())
        finally:
            popup_menu.grab_release()

    def _do_fill_down(self) -> None:
        """Copy value from first selected cell down"""
        sel_rows = self._chan_list.selected_rows()
        if len(sel_rows) <= 1:
            return

        # visible cols
        sel_cols = self._chan_list.selected_columns()
        if not sel_cols:
            sel_cols = self._chan_list.visible_cols()

        min_col, max_col = sel_cols[0], sel_cols[-1] + 1
        first_row = sel_rows[0]
        sheet = self._chan_list.sheet
        data = sheet[(first_row, min_col), (first_row + 1, max_col)].data

        with suppress(ValueError):
            # remove bank_pos if is on list
            idx = sel_cols.index(self._chan_list.colmap["bank_pos"])
            data[idx] = None

        for row in sel_rows[1:]:
            sheet.span((row, min_col), emit_event=True).data = data

    def _do_fill_freq(self) -> None:
        """Copy freq from first row increased by ts"""
        sel_rows = self._chan_list.selected_rows()
        if len(sel_rows) <= 1:
            return

        chan = self._chan_list.data[sel_rows[0]].obj
        if not chan or not chan.freq or chan.hide_channel:
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

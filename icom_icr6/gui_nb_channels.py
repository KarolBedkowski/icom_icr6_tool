# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from tkinter import messagebox, ttk

from . import consts, expimp, gui_chanlist, gui_model, model

_LOG = logging.getLogger(__name__)


class ChannelsPage(tk.Frame):
    _chan_list: gui_chanlist.ChannelsList[gui_chanlist.Row]

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

    def set(
        self, radio_memory: model.RadioMemory, *, activate: bool = False
    ) -> None:
        self._radio_memory = radio_memory

        # hide canceller in global models
        self._chan_list.set_hide_canceller(
            hide=not radio_memory.is_usa_model()
        )

        if activate:
            self._groups_list.selection_set(self._last_selected_group)

        self.__update_chan_list()

        if activate:
            self._chan_list.selection_set(self._last_selected_chan)

    def _create_channel_list(self, frame: tk.Frame) -> None:
        self._chan_list = gui_chanlist.ChannelsList(frame)
        self._chan_list.on_record_update = self.__on_channel_update
        self._chan_list.on_record_selected = self.__on_channel_select
        self._chan_list.on_channel_bank_validate = self.__on_channel_bank_set
        self._chan_list.pack(side=tk.TOP, expand=True, fill=tk.BOTH, ipady=6)
        # self._chan_list.bind("<Control-c>", self.__on_channel_copy)
        # self._chan_list.bind("<Control-v>", self.__on_channel_paste)

    def __on_channel_update(
        self, action: str, rows: ty.Collection[gui_chanlist.Row]
    ) -> None:
        for rec in rows:
            _LOG.debug("__on_channel_update: [%r]: %r", action, rec)
            chan = rec.channel
            self._radio_memory.set_channel(chan)

        if self.__need_full_refresh:
            self.__update_chan_list()
        else:
            self._show_stats()

    def __on_channel_select(self, rows: list[gui_chanlist.Row]) -> None:
        for rec in rows:
            _LOG.debug("chan selected: %r", rec.channel)

    def __update_chan_list(self, _event: tk.Event | None = None) -> None:  # type: ignore
        if sel := self._groups_list.curselection():  # type: ignore
            selected_range = sel[0]
        else:
            return

        self._last_selected_group = sel[0]

        range_start = selected_range * 100
        data = [
            self._radio_memory.get_channel(idx)
            for idx in range(range_start, range_start + 100)
        ]
        self._chan_list.set_data(data)

        self._show_stats()
        self.__need_full_refresh = False

    # def __on_channel_copy(self, _event: tk.Event) -> None:  # type: ignore
    #     sel = self._chan_list.selection()
    #     if not sel:
    #         return

    #     channels = (
    #         self._radio_memory.get_channel(int(chan_num)) for chan_num in sel
    #     )
    #     clip = gui_model.Clipboard.instance()
    #     clip.put(expimp.export_channel_str(channels))

    # def __on_channel_paste(self, _event: tk.Event) -> None:  # type: ignore
    #     sel = self._chan_list.selection()
    #     if not sel:
    #         return

    #     clip = gui_model.Clipboard.instance()

    #     try:
    #         rows = list(expimp.import_channels_str(ty.cast(str, clip.get())))
    #     except Exception:
    #         _LOG.exception("import from clipboard error")
    #         return

    #     # special case - when in clipboard is one record and selected  many-
    #     # duplicate
    #     if len(sel) > 1 and len(rows) == 1:
    #         row = rows[0]
    #         for spos in sel:
    #             if not self.__paste_channel(row, int(spos)):
    #                 break

    #     else:
    #         start_num = int(sel[0])
    #         for chan_num, row in enumerate(rows, start_num):
    #             if not self.__paste_channel(row, chan_num):
    #                 break
    #             # stop on range boundary
    #             if chan_num % 100 == 99:  # noQa: PLR2004
    #                 break

    #     self.__update_chan_list()

    # def __paste_channel(self, row: dict[str, object], chan_num: int) -> bool:
    #     chan = self._radio_memory.get_channel(chan_num).clone()
    #     # do not clean existing rows
    #     if not row.get("freq"):
    #         return True

    #     try:
    #         chan.from_record(row)
    #         chan.validate()
    #     except ValueError:
    #         _LOG.exception("import from clipboard error")
    #         _LOG.error("chan_num=%d, row=%r", chan_num, row)
    #         return False

    #     chan.hide_channel = False
    #     # do not set bank on paste
    #     chan.bank = consts.BANK_NOT_SET
    #     chan.bank_pos = 0
    #     self._radio_memory.set_channel(chan)

    #     return True

    def _show_stats(self) -> None:
        active = sum(
            1 for c in self._chan_list.data if c and not c.hide_channel
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

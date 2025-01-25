# Copyright © 2025 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

"""
Copy channels dialog.
"""

from __future__ import annotations

import logging
import tkinter as tk
import typing as ty
from tkinter import messagebox, simpledialog, ttk

from icom_icr6 import change_manager, config, consts, model

from . import widgets

_LOG = logging.getLogger(__name__)


class CopyChannelsDialog(simpledialog.Dialog):
    def __init__(
        self,
        parent: tk.Widget,
        cm: change_manager.ChangeManeger,
        channels: list[model.Channel],
        *,
        ro: bool = False,
    ) -> None:
        """
        Copy channels dialog.
        ro = read-only source channels (i.e. awchannels)
        """
        self._cm = cm
        self._channels = channels
        self._ro = ro
        self._dst_group = tk.StringVar()
        self._dst_bank = tk.StringVar()
        self._remove_after_copy = tk.IntVar()
        self._groups_names = list(self._get_groups_names())
        self._banks_names = list(self._get_banks_names())

        super().__init__(parent, "Copy channels")

    def body(self, master: tk.Widget) -> None:
        frame = tk.Frame(master)

        widgets.new_combo(
            frame,
            0,
            0,
            "Destination group: ",
            self._dst_group,
            self._groups_names,
        )

        widgets.new_combo(
            frame, 1, 0, "Set bank:", self._dst_bank, self._banks_names
        )

        if not self._ro:
            widgets.new_checkbox(
                frame,
                2,
                0,
                "Remove after copy",
                self._remove_after_copy,
                colspan=2,
            )

        frame.pack(side=tk.TOP, fill=tk.X)

    def buttonbox(self) -> None:
        box = tk.Frame(self)

        self._btn_ok = w = ttk.Button(
            box,
            text="Copy",
            width=10,
            command=self._on_ok,
            default=tk.ACTIVE,
        )
        w.pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(box, text="Cancel", width=10, command=self.cancel).pack(
            side=tk.LEFT, padx=5, pady=5
        )

        self.bind("<Return>", self._on_ok)
        self.bind("<Escape>", self.cancel)

        box.pack()

    def _on_close(self, _event: tk.Event | None = None) -> None:  # type:ignore
        self.grab_release()
        self.destroy()

    def _on_ok(self, _event: tk.Event | None = None) -> None:  # type: ignore
        dst_group = self._get_selected_group()
        if dst_group is None:
            return

        rm = self._cm.rm
        num_channels = len(self._channels)

        # check if there is enough free space
        hidden_channels = rm.get_hidden_channels_in_group(dst_group)
        if len(hidden_channels) < num_channels and not messagebox.askokcancel(
            "Copy channels",
            f"There are only {len(hidden_channels)} free spaces in group. "
            f"(required  {num_channels}).\n"
            "Continue and copy only part of channels?",
        ):
            return

        set_bank = self._get_selected_bank()
        bank_pos = []

        if set_bank is not None and set_bank >= 0:
            bank_pos = rm.get_bank_free_pos(set_bank)
            if len(bank_pos) < num_channels and not messagebox.askokcancel(
                "Copy channels",
                f"There are only {len(bank_pos)} free positions in bank "
                f"(required {num_channels}).\n"
                "Continue and copy only Copy only part?",
            ):
                return

        remove = self._remove_after_copy.get() == 1

        for src_chan, dst_chan in zip(
            self._channels, hidden_channels, strict=False
        ):
            self._copy_channel(
                src_chan, dst_chan, set_bank, bank_pos, remove=remove
            )

        self._cm.commit()
        super().ok()

    def _copy_channel(
        self,
        src_chan: model.Channel,
        dst_chan: model.Channel,
        set_bank: int | None,
        bank_pos: list[int],
        *,
        remove: bool,
    ) -> None:
        _LOG.debug("copy %s -> %d", src_chan, dst_chan.number)
        dst_chan = dst_chan.clone()
        dst_chan.copy_from(src_chan)
        dst_chan.hide_channel = False
        self._cm.set_channel(dst_chan)

        src_modified = False

        if set_bank == -1:
            # move bank position to new channel;
            dst_chan.bank = src_chan.bank
            dst_chan.bank_pos = src_chan.bank_pos
            src_chan = src_chan.clone()
            src_chan.clear_bank()
            src_modified = True

        elif set_bank is not None and bank_pos:
            # set new bank pos
            dst_chan.bank = set_bank
            dst_chan.bank_pos = bank_pos.pop(0)

        if remove:
            # remove old channel
            src_chan = src_chan.clone()
            src_chan.hide_channel = True
            src_modified = True

        if src_modified:
            self._cm.set_channel(src_chan)

    def _get_groups_names(self) -> ty.Iterable[str]:
        for idx in range(13):
            if name := config.CONFIG.chan_group_names[idx]:
                yield f"{idx:>2}xx {name}"

            else:
                yield f"{idx:>2}xx"

    def _get_selected_group(self) -> int | None:
        group = self._dst_group.get()
        if not group:
            return None

        return self._groups_names.index(group)

    def _get_banks_names(self) -> ty.Iterable[str]:
        if not self._ro:
            yield "Set original bank and position"

        for idx in range(consts.NUM_BANKS):
            yield self._cm.rm.get_bank_fullname(idx)  # type: ignore

    def _get_selected_bank(self) -> int | None:
        bank = self._dst_bank.get()
        if not bank:
            return None

        if self._ro:
            return self._banks_names.index(bank)

        return self._banks_names.index(bank) - 1

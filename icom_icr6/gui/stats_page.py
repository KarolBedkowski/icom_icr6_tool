# Copyright © 2025 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
import typing as ty
from tkinter import ttk

from icom_icr6 import consts
from icom_icr6.change_manager import ChangeManeger

from . import support

_LOG = logging.getLogger(__name__)


class StatsPage(tk.Frame):
    def __init__(self, parent: tk.Widget, cm: ChangeManeger) -> None:
        super().__init__(parent)

        self._change_manager = cm
        self._create_result_tree()

    def update_tab(self) -> None:
        tree = self._result_tree
        tree.delete(*tree.get_children())

        for category, items in self._get_data():
            ciid = tree.insert("", tk.END, text=category, open=True)
            for key, value in items:
                tree.insert(ciid, tk.END, text=key, values=(str(value),))

    def reset(self) -> None:
        pass

    def _create_result_tree(self) -> None:
        frame = tk.Frame(self)
        self._result_tree = tree = ttk.Treeview(
            frame,
            selectmode=tk.BROWSE,
            columns=("data"),
        )
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        tree.configure(yscrollcommand=vsb.set)

        frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=12)

    def _get_data(
        self,
    ) -> ty.Iterable[tuple[str, ty.Iterable[tuple[str, object]]]]:
        yield ("Channels", self._get_data_channels())
        yield ("Bands", self._get_data_bands())

    def _get_data_channels(self) -> ty.Iterable[tuple[str, object]]:
        rm = self._change_manager.rm
        yield (
            "Total number of active channels",
            sum(1 for c in rm.get_active_channels()),
        )
        yield (
            "Total number of active channels in banks",
            sum(
                c.bank != consts.BANK_NOT_SET for c in rm.get_active_channels()
            ),
        )
        yield (
            "Total number of active channels without bank",
            sum(
                c.bank == consts.BANK_NOT_SET for c in rm.get_active_channels()
            ),
        )

    def _get_data_bands(self) -> ty.Iterable[tuple[str, object]]:
        rm = self._change_manager.rm
        prev_band = 100_000
        for band in rm.get_bands_range():
            cnt = sum(
                1
                for c in rm.get_active_channels()
                if prev_band <= c.freq < band
            )
            yield (
                f"Channels in {support.format_freq(prev_band)} "
                f"- {support.format_freq(band)}",
                cnt,
            )
            prev_band = band

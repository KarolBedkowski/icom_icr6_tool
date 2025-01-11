# Copyright © 2025 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

"""
Display reports.
"""

from __future__ import annotations

import logging
import tkinter as tk
import typing as ty
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from icom_icr6 import config, reports

if ty.TYPE_CHECKING:
    from icom_icr6.radio_memory import RadioMemory

_LOG = logging.getLogger(__name__)

_REPORTS = ["Statistics", "Sheet"]


class ReportsDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        radio_memory: RadioMemory,
    ) -> None:
        super().__init__(parent)
        self.title("Find")

        self._radio_memory = radio_memory
        self._sel_report = tk.StringVar()

        main_frame = tk.Frame(self)
        self._create_frame_top(main_frame)
        self._create_frame_result(main_frame)

        main_frame.pack(
            side=tk.TOP, fill=tk.BOTH, expand=True, pady=12, padx=12
        )

        self.bind("<Escape>", self._on_close)
        self.bind("<Destroy>", self._on_destroy)
        self.geometry(config.CONFIG.reports_window_geometry)

        self._on_generate_report()

    def _create_frame_top(self, parent: tk.Frame) -> None:
        frame_top = tk.Frame(parent)

        ttk.Label(frame_top, text="Report: ").pack(
            side=tk.LEFT,
            expand=False,
            fill=tk.Y,
            padx=6,
        )
        cb = ttk.Combobox(
            frame_top,
            textvariable=self._sel_report,
            exportselection=False,
            state="readonly",
            values=_REPORTS,
        )
        cb.pack(side=tk.LEFT, padx=6, expand=False)
        cb.bind("<<ComboboxSelected>>", self._on_generate_report)
        self._sel_report.set(_REPORTS[0])

        ttk.Button(
            frame_top,
            text="Save...",
            command=self._on_save_report,
        ).pack(side=tk.RIGHT, padx=6, pady=6)

        frame_top.pack(side=tk.TOP, fill=tk.X, pady=6)

    def _create_frame_result(self, parent: tk.Frame) -> None:
        frame = tk.Frame(parent)
        self._result = tk.Text(frame)
        self._result.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(
            frame, orient="vertical", command=self._result.yview
        )
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self._result.configure(yscrollcommand=vsb.set)

        frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=6)

    def _on_destroy(self, event: tk.Event) -> None:  # type: ignore
        if event.widget == self:
            config.CONFIG.reports_window_geometry = self.geometry()

    def _on_close(self, _event: tk.Event | None = None) -> None:  # type:ignore
        self.grab_release()
        self.destroy()

    def _on_generate_report(self, _event: tk.Event | None = None) -> None:  # type: ignore
        self._result.delete("1.0", tk.END)
        data = ""

        match self._sel_report.get():
            case "Statistics":
                data = "\n".join(reports.generate_stats(self._radio_memory))
            case "Sheet":
                data = "\n".join(reports.generate_sheet(self._radio_memory))

        self._result.insert(tk.END, data)

    def _on_save_report(self) -> None:
        report = self._sel_report.get().lower()
        fname = filedialog.asksaveasfilename(
            parent=self,
            filetypes=[("Text files", ".txt"), ("All files", "*.*")],
            initialfile=f"{report}.txt",
            defaultextension=".txt",
        )
        if fname:
            data = self._result.get("1.0", tk.END)
            try:
                with Path(fname).open("wt") as ofile:
                    ofile.write(data)
            except Exception as err:
                _LOG.exception("save report error")
                messagebox.showerror("Save file error", str(err))

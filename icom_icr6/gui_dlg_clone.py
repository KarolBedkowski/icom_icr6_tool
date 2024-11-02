# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import tkinter as tk
from pathlib import Path
from tkinter import simpledialog, ttk

from . import io, model


class _CloneDialog(simpledialog.Dialog):
    def body(self, master: tk.Widget) -> None:
        self._var_port = tk.StringVar()
        self._var_progress = tk.StringVar()

        tk.Label(master, text="Port: ").grid(
            row=0, column=0, sticky=tk.N + tk.W + tk.S, padx=6, pady=6
        )
        ttys = [
            str(p) for p in Path("/dev/").iterdir() if p.name.startswith("tty")
        ]
        self._var_port.set(ttys[0])
        ttk.Combobox(
            master,
            values=ttys,
            exportselection=False,
            textvariable=self._var_port,
        ).grid(row=0, column=1, sticky=tk.N + tk.W + tk.E, padx=6, pady=6)

        tk.Label(master, text="", textvariable=self._var_progress).grid(
            row=1, column=0, columnspan=2, sticky=tk.N + tk.W, padx=6, pady=6
        )

    def buttonbox(self) -> None:
        box = tk.Frame(self)

        w = tk.Button(
            box,
            text="Start clone",
            width=10,
            command=self.ok,
            default=tk.ACTIVE,
        )
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        box.pack()


class CloneFromRadioDialog(_CloneDialog):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, "Clone from radio")
        self.radio_memory: model.RadioMemory | None = None

    def __progress_cb(self, progress: int) -> bool:
        self._var_progress.set(f"Read: {progress}")
        return True

    def ok(self, _event: tk.Event | None = None) -> None:  # type: ignore
        self._var_progress.set("Starting...")
        radio = io.Radio(self._var_port.get())
        try:
            self.radio_memory = radio.clone_from(self.__progress_cb)
            self._var_progress.set("Done")
        except io.AbortError:
            self.radio_memory = None
            self.cancel()
        except Exception as err:
            self._var_progress.set(f"ERROR: {err}")
            self.radio_memory = None
        else:
            super().ok()
            return

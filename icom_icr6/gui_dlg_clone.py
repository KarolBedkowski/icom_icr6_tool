# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import tkinter as tk
from pathlib import Path
from tkinter import simpledialog, ttk

from . import consts, io, model
from .radio_memory import RadioMemory

_LOG = logging.getLogger(__name__)


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
        # self._var_port.set(ttys[0])
        self._var_port.set("/dev/ttyUSB0")
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
        self.radio_memory: RadioMemory | None = None
        super().__init__(parent, "Clone from radio")

    def __progress_cb(self, progress: int) -> bool:
        perc = min(100 * progress / consts.MEM_SIZE, 100.0)
        self._var_progress.set(f"Read: {perc:0.1f}%")
        self.update_idletasks()
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
            _LOG.exception("clone from radio error")
            self._var_progress.set(f"ERROR: {err}")
            self.radio_memory = None
        else:
            super().ok()


class CloneToRadioDialog(_CloneDialog):
    def __init__(self, parent: tk.Widget, radio_memory: RadioMemory) -> None:
        self._radio_memory = radio_memory
        self.result = False
        super().__init__(parent, "Clone to radio")

    def __progress_cb(self, progress: int) -> bool:
        perc = min(100 * progress / consts.MEM_SIZE, 100.0)
        self._var_progress.set(f"Write: {perc:0.1f}%")
        self.update_idletasks()
        return True

    def ok(self, _event: tk.Event | None = None) -> None:  # type: ignore
        self._var_progress.set("Starting...")
        radio = io.Radio(self._var_port.get())
        try:
            radio.clone_to(self._radio_memory, self.__progress_cb)
            self._var_progress.set("Done")
        except io.AbortError:
            self.cancel()
        except Exception as err:
            _LOG.exception("clone to radio error")
            self._var_progress.set(f"ERROR: {err}")
        else:
            self.result = True
            super().ok()


class RadioInfoDialog(_CloneDialog):
    def __init__(self, parent: tk.Widget) -> None:
        self.result: model.RadioModel | None = None
        super().__init__(parent, "Radio info")

    def ok(self, _event: tk.Event | None = None) -> None:  # type: ignore
        radio = io.Radio(self._var_port.get())
        try:
            self.result = radio.get_model()
        except io.AbortError:
            self.cancel()
        except Exception as err:
            _LOG.exception("get info radio error")
            self._var_progress.set(f"ERROR: {err}")
        else:
            super().ok()

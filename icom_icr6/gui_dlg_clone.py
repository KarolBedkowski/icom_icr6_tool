# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import queue
import threading
import tkinter as tk
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from tkinter import simpledialog, ttk

from . import config, consts, io, model
from .radio_memory import RadioMemory

_LOG = logging.getLogger(__name__)


@dataclass
class _Result:
    progress: int = 0
    status: str = ""
    result: object = None
    error: str = ""


class _CloneDialog(simpledialog.Dialog):
    def body(self, master: tk.Widget) -> None:
        self._var_port = tk.StringVar()
        self._var_progress = tk.StringVar()
        self._var_hispeed = tk.IntVar()

        tk.Label(master, text="Port: ").grid(
            row=0, column=0, sticky=tk.N + tk.W + tk.S, padx=6, pady=6
        )
        ttys = [
            str(p) for p in Path("/dev/").iterdir() if p.name.startswith("tty")
        ]

        self._var_port.set(config.CONFIG.last_port)
        ttk.Combobox(
            master,
            values=ttys,
            exportselection=False,
            textvariable=self._var_port,
        ).grid(row=0, column=1, sticky=tk.N + tk.W + tk.E, padx=6, pady=6)

        ttk.Checkbutton(
            master,
            text="Use hispeed mode",
            onvalue=1,
            offvalue=0,
            variable=self._var_hispeed,
        ).grid(
            row=1,
            column=0,
            sticky=tk.N + tk.W + tk.E,
            padx=6,
            pady=6,
            columnspan=2,
        )
        self._var_hispeed.set(1 if config.CONFIG.hispeed else 0)

        tk.Label(master, text="", textvariable=self._var_progress).grid(
            row=2, column=0, columnspan=2, sticky=tk.N + tk.W, padx=6, pady=6
        )

    def buttonbox(self) -> None:
        box = tk.Frame(self)

        self._btn_ok = w = ttk.Button(
            box,
            text="Start clone",
            width=10,
            command=self.ok,
            default=tk.ACTIVE,
        )
        w.pack(side=tk.LEFT, padx=5, pady=5)
        self._btn_cancel = w = ttk.Button(
            box, text="Cancel", width=10, command=self.cancel
        )
        w.pack(side=tk.LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        box.pack()


class CloneFromRadioDialog(_CloneDialog):
    def __init__(self, parent: tk.Widget) -> None:
        self.radio_memory: RadioMemory | None = None
        self._working = False
        self._bg_task_queue: queue.Queue[_Result] = queue.Queue()
        self._bg_task: CloneFromTask | None = None
        super().__init__(parent, "Clone from radio")

    def __progress_cb(self, progress: int) -> bool:
        perc = min(100 * progress / consts.MEM_SIZE, 100.0)
        self._var_progress.set(f"Read: {perc:0.1f}%")
        self.update_idletasks()
        return True

    def ok(self, _event: tk.Event | None = None) -> None:  # type: ignore
        if self._working:
            return

        self._working = True
        self._var_progress.set("Starting...")
        self.update_idletasks()

        config.CONFIG.last_port = port = self._var_port.get()
        config.CONFIG.hispeed = hispeed = bool(self._var_hispeed.get())

        # disable buttons
        self._btn_ok["state"] = "disabled"

        # start bg task
        self._bg_task = CloneFromTask(self._bg_task_queue, port, hispeed)
        self._bg_task.start()
        self.master.after(250, self._monitor_bg_task)

    def cancel(self, _event: tk.Event | None = None) -> None:  # type: ignore
        if self._working:
            assert self._bg_task
            self._bg_task.abort = True

        else:
            super().cancel()

    def _monitor_bg_task(self) -> None:
        with suppress(queue.Empty):
            while True:
                res = self._bg_task_queue.get_nowait()
                if res.status == "finished":
                    assert res.result
                    assert isinstance(res.result, RadioMemory)
                    self.radio_memory = res.result
                    self._var_progress.set("Done")
                    self.update_idletasks()
                    super().ok()
                    return

                if res.status == "abort":
                    self._on_stop_working("Aborted")
                    return

                if res.status == "error":
                    self._on_stop_working(f"ERROR: {res.error}")
                    return

                if res.status == "status":
                    self.__progress_cb(res.progress)

        self.after(250, self._monitor_bg_task)

    def _on_stop_working(self, msg: str) -> None:
        self.radio_memory = None
        self._btn_ok["state"] = ""
        self._working = False
        self._var_progress.set(msg)


class CloneFromTask(threading.Thread):
    def __init__(
        self,
        queue: queue.Queue[_Result],
        port: str,
        hispeed: bool,  # noqa: FBT001
    ) -> None:
        super().__init__()
        self.queue = queue
        self.port = port
        self.hispeed = hispeed
        self.abort = False

    def __progress_cb(self, progress: int) -> bool:
        self.queue.put(_Result(progress=progress, status="status"))
        return not self.abort

    def run(self) -> None:
        radio = io.Radio(self.port, hispeed=self.hispeed)
        try:
            radio_memory = radio.clone_from(self.__progress_cb)

        except io.AbortError:
            self.queue.put(_Result(status="abort"))

        except Exception as err:
            _LOG.exception("clone from radio error")
            self.queue.put(_Result(status="error", error=str(err)))

        else:
            self.queue.put(_Result(status="finished", result=radio_memory))


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
        self.update_idletasks()

        config.CONFIG.last_port = port = self._var_port.get()
        config.CONFIG.hispeed = hispeed = bool(self._var_hispeed.get())

        radio = io.Radio(port, hispeed=hispeed)
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

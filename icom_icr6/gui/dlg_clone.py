# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import builtins
import logging
import queue
import threading
import tkinter as tk
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from tkinter import simpledialog, ttk

from icom_icr6 import config, consts, ic_io, model
from icom_icr6.radio_memory import RadioMemory

_LOG = logging.getLogger(__name__)


@dataclass
class _Result:
    progress: int = 0
    status: str = ""
    result: object = None
    error: str = ""


class _CloneTask(threading.Thread):
    def __init__(
        self,
        result_queue: queue.Queue[_Result],
        port: str,
        hispeed: bool,  # noqa: FBT001
    ) -> None:
        super().__init__()
        self.queue = result_queue
        self.port = port
        self.hispeed = hispeed
        self.abort = False

    def _progress_cb(self, progress: int) -> bool:
        if self.queue.empty():
            self.queue.put(_Result(progress=progress, status="status"))

        return not self.abort


class _CloneDialog(simpledialog.Dialog):
    def __init__(self, parent: tk.Widget, title: str) -> None:
        self._working = False
        self._bg_task_queue: queue.Queue[_Result] = queue.Queue()
        self._bg_task: _CloneTask | None = None
        super().__init__(parent, title)

    def body(self, master: tk.Widget) -> None:
        self._var_port = tk.StringVar()
        self._var_progress = tk.StringVar()
        self._var_hispeed = tk.IntVar()

        frame = tk.Frame(master)
        ttk.Label(frame, text="Port: ").pack(side=tk.LEFT, padx=6, pady=6)
        ttys = [
            str(p) for p in Path("/dev/").iterdir() if p.name.startswith("tty")
        ]

        self._var_port.set(config.CONFIG.last_port)
        ttk.Combobox(
            frame,
            values=ttys,
            exportselection=False,
            textvariable=self._var_port,
        ).pack(side=tk.LEFT, expand=True, padx=6, pady=6)

        frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Checkbutton(
            master,
            text="Use hispeed mode",
            onvalue=1,
            offvalue=0,
            variable=self._var_hispeed,
        ).pack(side=tk.TOP, fill=tk.X)
        self._var_hispeed.set(1 if config.CONFIG.hispeed else 0)

        tk.Message(master, aspect=500, textvariable=self._var_progress).pack(
            side=tk.TOP, fill=tk.BOTH, expand=True, padx=6, pady=6
        )

    def buttonbox(self) -> None:
        box = tk.Frame(self)

        self._btn_ok = w = ttk.Button(
            box,
            text="Start clone",
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

    def _progress_cb(self, progress: int) -> bool:
        perc = min(100 * progress / consts.MEM_SIZE, 100.0)
        self._var_progress.set(f"Done: {perc:0.1f}%")
        self.update_idletasks()
        return True

    def cancel(self, _event: tk.Event | None = None) -> None:  # type: ignore
        if self._working:
            assert self._bg_task
            self._bg_task.abort = True

        else:
            super().cancel()

    def _start_working(self) -> None:
        self._working = True
        self._btn_ok["state"] = "disabled"
        self._var_progress.set("Starting...")
        self.update_idletasks()

    def _stop_working(self, msg: str) -> None:
        self._btn_ok["state"] = ""
        self._working = False
        self._var_progress.set(msg)

    def _on_ok(self, _event: tk.Event | None = None) -> None:  # type: ignore
        raise NotImplementedError

    def _on_success(self, result: object) -> None:
        raise NotImplementedError

    def _monitor_bg_task(self) -> None:
        with suppress(queue.Empty):
            while True:
                res = self._bg_task_queue.get_nowait()

                if res.status == "status":
                    self._progress_cb(res.progress)
                    continue

                if res.status == "finished":
                    _LOG.debug("bg task finished")
                    self._var_progress.set("Done")
                    self.update_idletasks()
                    self._on_success(res.result)
                    self.destroy()
                    return

                if res.status == "abort":
                    self._stop_working(
                        "Aborted. Radio may still sending or receiving data."
                    )
                    return

                if res.status == "error":
                    self._stop_working(f"ERROR: {res.error}.")
                    return

                _LOG.error("unknown result: %r", res)

        self.after(250, self._monitor_bg_task)

    def _check_port(self) -> tuple[str, bool]:
        port = self._var_port.get().strip()
        if not port and not getattr(builtins, "APP_DEV_MODE", False):
            self._var_progress.set("ERROR: port not selected")
            return "", False

        return port, True


class CloneFromRadioDialog(_CloneDialog):
    def __init__(self, parent: tk.Widget) -> None:
        self.radio_memory: RadioMemory | None = None
        super().__init__(parent, "Clone from radio")

    def _on_ok(self, _event: tk.Event | None = None) -> None:  # type: ignore
        if self._working:
            return

        port, ok = self._check_port()
        if not ok:
            return

        self._start_working()

        config.CONFIG.last_port = port
        config.CONFIG.hispeed = hispeed = bool(self._var_hispeed.get())

        # start bg task
        self._bg_task = _CloneFromTask(self._bg_task_queue, port, hispeed)
        self._bg_task.start()
        self.after(250, self._monitor_bg_task)

    def _on_success(self, result: object) -> None:
        assert isinstance(result, RadioMemory)
        self.radio_memory = result


class _CloneFromTask(_CloneTask):
    def run(self) -> None:
        radio = ic_io.Radio(self.port, hispeed=self.hispeed)
        try:
            radio_memory = radio.clone_from(self._progress_cb)

        except ic_io.AbortError:
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

    def _on_ok(self, _event: tk.Event | None = None) -> None:  # type: ignore
        if self._working:
            return

        port, ok = self._check_port()
        if not ok:
            return

        self._start_working()

        config.CONFIG.last_port = port
        config.CONFIG.hispeed = hispeed = bool(self._var_hispeed.get())

        # start bg task
        self._bg_task = _CloneToTask(
            self._bg_task_queue, port, hispeed, self._radio_memory
        )
        self._bg_task.start()
        self.after(250, self._monitor_bg_task)

    def _on_success(self, result: object) -> None:
        _ = result
        self.result = True


class _CloneToTask(_CloneTask):
    def __init__(
        self,
        result_queue: queue.Queue[_Result],
        port: str,
        hispeed: bool,  # noqa: FBT001
        radio_memory: RadioMemory,
    ) -> None:
        super().__init__(result_queue, port, hispeed)
        self._radio_memory = radio_memory

    def run(self) -> None:
        radio = ic_io.Radio(self.port, hispeed=self.hispeed)
        try:
            radio.clone_to(self._radio_memory, self._progress_cb)

        except ic_io.AbortError:
            self.queue.put(_Result(status="abort"))

        except Exception as err:
            _LOG.exception("clone to radio error")
            self.queue.put(_Result(status="error", error=str(err)))

        else:
            self.queue.put(_Result(status="finished"))


class RadioInfoDialog(_CloneDialog):
    def __init__(self, parent: tk.Widget) -> None:
        self.result: model.RadioModel | None = None
        super().__init__(parent, "Radio info")

    def _on_ok(self, _event: tk.Event | None = None) -> None:  # type: ignore
        port, ok = self._check_port()
        if not ok:
            return

        radio = ic_io.Radio(port)
        try:
            self.result = radio.get_model()

        except ic_io.AbortError:
            self.cancel()

        except Exception as err:
            _LOG.exception("get info radio error")
            self._var_progress.set(f"ERROR: {err}")

        else:
            super().ok()

    def _on_success(self, result: object) -> None:
        pass

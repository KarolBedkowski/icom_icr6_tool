# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from . import (
    gui_model,
    gui_nb_awchannels,
    gui_nb_banks,
    gui_nb_channels,
    gui_nb_scan_edge,
    gui_nb_scan_links,
    gui_nb_settings,
    io,
    model,
)

_LOG = logging.getLogger(__name__)


class App(tk.Frame):
    def __init__(self, master: tk.Tk, file: Path | None) -> None:
        super().__init__(master)

        self._last_file: Path | None = None
        self._radio_memory = model.RadioMemory()
        self._channel_model = gui_model.ChannelModel()

        self.pack(fill="both", expand=1)

        self.__create_menu(master)

        self._ntb = ttk.Notebook(self)
        self._ntb.add(self.__create_nb_channels(), text="Channels")
        self._ntb.add(self.__create_nb_banks(), text="Banks")
        self._ntb.add(self.__create_nb_scan_edge(), text="Scan Edge")
        self._ntb.add(self.__create_nb_scan_links(), text="Scan Link")
        self._ntb.add(self.__create_nb_awchannels(), text="Autowrite channels")
        self._ntb.add(self.__create_nb_settings(), text="Settings")
        self._ntb.bind("<<NotebookTabChanged>>", self.__on_nb_page_changed)

        self._ntb.pack(fill="both", expand=1)

        if file:
            self.load_icf(file)

    def __create_menu(self, master: tk.Tk) -> None:
        menu_bar = tk.Menu(master)
        master.config(menu=menu_bar)

        file_menu = tk.Menu(menu_bar)
        file_menu.add_command(
            label="Open...", command=self.__on_file_open, accelerator="Ctrl+O"
        )
        master.bind_all("<Control-o>", self.__on_file_open)
        file_menu.add_command(
            label="Save...", command=self.__on_file_save, accelerator="Ctrl+S"
        )
        master.bind_all("<Control-s>", self.__on_file_save)
        file_menu.add_command(
            label="Save As...",
            command=self.__on_file_save_as,
            accelerator="Shift+Ctrl+S",
        )
        master.bind_all("<Shift-Control-S>", self.__on_file_save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menu_bar)
        help_menu.add_command(label="About", command=self.__on_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)

    def __create_nb_channels(self) -> tk.Widget:
        self._nb_channels = gui_nb_channels.ChannelsPage(
            self, self._radio_memory
        )
        return self._nb_channels

    def __create_nb_banks(self) -> tk.Widget:
        self._nb_banks = gui_nb_banks.BanksPage(self, self._radio_memory)
        return self._nb_banks

    def __create_nb_scan_edge(self) -> tk.Frame:
        self._nb_scan_edge = gui_nb_scan_edge.ScanEdgePage(
            self, self._radio_memory
        )
        return self._nb_scan_edge

    def __create_nb_scan_links(self) -> tk.Widget:
        self._nb_scan_links = gui_nb_scan_links.ScanLinksPage(
            self, self._radio_memory
        )
        return self._nb_scan_links

    def __create_nb_awchannels(self) -> tk.Widget:
        self._nb_aw_channels = gui_nb_awchannels.AutoWriteChannelsPage(
            self, self._radio_memory
        )
        return self._nb_aw_channels

    def __create_nb_settings(self) -> tk.Widget:
        self._nb_settings = gui_nb_settings.SettingsPage(
            self, self._radio_memory
        )
        return self._nb_settings

    def __on_about(self) -> None:
        pass

    def __on_file_open(self, _event: tk.Event | None = None) -> None:  # type: ignore
        fname = filedialog.askopenfilename(
            parent=self,
            filetypes=[("Supported files", ".icf"), ("All files", "*.*")],
            initialdir=str(self._last_file.parent) if self._last_file else ".",
            defaultextension=".icf",
        )

        if fname:
            self.load_icf(Path(fname))

        self.focus_set()

    def load_icf(self, file: Path) -> None:
        self._radio_memory.update_from(io.load_icf_file(file))
        self._last_file = file
        self.__update_widgets()

    def __on_file_save(self, _event: tk.Event | None = None) -> None:  # type: ignore
        if not self._last_file:
            self.__on_file_save_as()
            return

        io.save_icf_file(self._last_file, self._radio_memory)
        self.focus_set()

    def __on_file_save_as(self, _event: tk.Event | None = None) -> None:  # type: ignore
        fname = filedialog.asksaveasfilename(
            parent=self,
            filetypes=[("Supported files", ".icf"), ("All files", "*.*")],
            initialdir=str(self._last_file.parent) if self._last_file else ".",
            initialfile=self._last_file.name if self._last_file else "",
            defaultextension=".icf",
        )

        if fname:
            self._last_file = Path(fname)
            io.save_icf_file(self._last_file, self._radio_memory)

        self.focus_set()

    def __update_widgets(self, page: int | None = None) -> None:
        _LOG.debug("update page: %r", page)
        pages = (
            self._nb_channels,
            self._nb_banks,
            self._nb_scan_edge,
            self._nb_scan_links,
            self._nb_aw_channels,
            self._nb_settings,
        )

        if page is None:
            for p in pages:
                p.set(self._radio_memory)

        else:
            pages[page].set(self._radio_memory)

    def __on_nb_page_changed(self, _event: tk.Event) -> None:  # type: ignore
        selected_tab = self._ntb.tabs().index(self._ntb.select())  # type: ignore
        self.__update_widgets(selected_tab)


def start_gui() -> None:
    file = Path(sys.argv[1]) if len(sys.argv) > 1 else None

    root = tk.Tk()
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("pad.TEntry", padding="1 1 1 1")
    myapp = App(root, file)
    root.geometry("1024x768")
    root.lift()

    myapp.mainloop()

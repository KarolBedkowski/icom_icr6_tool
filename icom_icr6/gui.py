# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import sys
import tkinter as tk
import typing as ty
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

_ty = ty


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

        self._ntb.pack(fill="both", expand=1)

        if file:
            self.load_icf(file)

    def __create_menu(self, master: tk.Tk) -> None:
        menu_bar = tk.Menu(master)
        master.config(menu=menu_bar)

        file_menu = tk.Menu(menu_bar)
        file_menu.add_command(
            label="Open...", command=self.__file_open_handler
        )
        file_menu.add_command(
            label="Save...", command=self.__file_save_handler
        )
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menu_bar)
        help_menu.add_command(label="About", command=self.__about_handler)
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

    def __about_handler(self) -> None:
        pass

    def __file_open_handler(self) -> None:
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
        self.__fill_widgets()

    def __file_save_handler(self) -> None:
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

    def __fill_widgets(self) -> None:
        self._nb_channels.set(self._radio_memory)
        self._nb_banks.set(self._radio_memory)
        self._nb_scan_edge.set(self._radio_memory)
        self._nb_scan_links.set(self._radio_memory)
        self._nb_aw_channels.set(self._radio_memory)
        self._nb_settings.set(self._radio_memory)


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

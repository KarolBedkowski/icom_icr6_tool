# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import logging
import sys
import tkinter as tk
import typing as ty
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import (
    expimp,
    gui_dlg_clone,
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


@ty.runtime_checkable
class TabWidget(ty.Protocol):
    def update_tab(self, radio_memory: model.RadioMemory) -> None: ...


class App(tk.Frame):
    def __init__(self, master: tk.Tk, file: Path | None) -> None:
        super().__init__(master)
        self.master = master

        self._last_file: Path | None = None
        self._radio_memory = model.RadioMemory()
        self._channel_model = gui_model.ChannelModel()
        self._status_value = tk.StringVar()
        # safe is clone to device when data are loaded or cloned from dev
        self._safe_for_clone = False

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

        self._ntb.pack(fill="both", expand=True)

        tk.Label(self, text="", textvariable=self._status_value).pack(
            side=tk.LEFT,
            fill=tk.X,
        )

        if file:
            self.load_icf(file)

    def set_status(self, msg: str) -> None:
        self._status_value.set(msg)

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

        export_menu = self.__create_menu_export(file_menu)
        file_menu.add_cascade(label="Export...", menu=export_menu)

        file_menu.add_separator()

        file_menu.add_command(label="Exit", command=self.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)

        radio_menu = tk.Menu(menu_bar)
        radio_menu.add_command(
            label="Clone from radio...", command=self.__on_clone_from_radio
        )
        radio_menu.add_command(
            label="Clone to radio...", command=self.__on_clone_to_radio
        )
        radio_menu.add_command(label="Info...", command=self.__on_radio_info)
        menu_bar.add_cascade(label="Radio", menu=radio_menu)

        help_menu = tk.Menu(menu_bar)
        help_menu.add_command(label="About", command=self.__on_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)

    def __create_menu_export(self, parent: tk.Menu) -> tk.Menu:
        menu = tk.Menu(parent)
        menu.add_command(
            label="Channels...",
            command=lambda: self.__on_export("channels"),
        )
        menu.add_command(
            label="Autowrrite channels...",
            command=lambda: self.__on_export("awchannels"),
        )
        return menu

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
        from . import VERSION

        messagebox.showinfo(
            "About",
            f"Icom IC-R6 tool\nVersion: {VERSION}\n\n"
            "Future information in README.rst, COPYING files.",
        )

    def __on_file_open(self, _event: tk.Event | None = None) -> None:  # type: ignore
        fname = filedialog.askopenfilename(
            parent=self,
            filetypes=[("Supported files", ".icf"), ("All files", "*.*")],
            initialdir=str(self._last_file.parent) if self._last_file else ".",
            defaultextension=".icf",
        )

        if fname:
            self.load_icf(Path(fname))

    def load_icf(self, file: Path) -> None:
        self._radio_memory.update_from(io.load_icf_file(file))
        self.__set_loaded_filename(file)
        self.__update_widgets()
        self.set_status(f"File {file} loaded")
        self._safe_for_clone = True

    def __on_file_save(self, _event: tk.Event | None = None) -> None:  # type: ignore
        if not self._last_file:
            self.__on_file_save_as()
            return

        io.save_icf_file(self._last_file, self._radio_memory)
        self.set_status(f"File {self._last_file} saved")

    def __on_file_save_as(self, _event: tk.Event | None = None) -> None:  # type: ignore
        fname = filedialog.asksaveasfilename(
            parent=self,
            filetypes=[("Supported files", ".icf"), ("All files", "*.*")],
            initialdir=str(self._last_file.parent) if self._last_file else ".",
            initialfile=self._last_file.name if self._last_file else "",
            defaultextension=".icf",
        )

        if fname:
            self.__set_loaded_filename(Path(fname))
            assert self._last_file
            io.save_icf_file(self._last_file, self._radio_memory)
            self.set_status(f"File {fname} saved")

    def __update_widgets(self) -> None:
        try:
            selected_tab = self._ntb.tabs().index(self._ntb.select())  # type: ignore
        except ValueError:
            selected_tab = 0

        _LOG.debug("update page: %r", selected_tab)

        pages: tuple[TabWidget, ...] = (
            self._nb_channels,
            self._nb_banks,
            self._nb_scan_edge,
            self._nb_scan_links,
            self._nb_aw_channels,
            self._nb_settings,
        )
        pages[selected_tab].update_tab(self._radio_memory)

    def __on_nb_page_changed(self, _event: tk.Event) -> None:  # type: ignore
        self.set_status("")
        self.__update_widgets()

    def __set_loaded_filename(self, fname: Path | None) -> None:
        self._last_file = fname
        title = f" [{fname.name}]" if fname else ""
        self.master.title(f"ICOM IC-R6 Tool{title}")  # type: ignore

    def __on_clone_from_radio(self, _event: tk.Event | None = None) -> None:  # type: ignore
        dlg = gui_dlg_clone.CloneFromRadioDialog(self)
        if dlg.radio_memory:
            self._radio_memory.update_from(dlg.radio_memory)
            self._safe_for_clone = True
            self.__set_loaded_filename(None)
            self.__update_widgets()

    def __on_clone_to_radio(self, _event: tk.Event | None = None) -> None:  # type: ignore
        if not self._safe_for_clone:
            messagebox.showerror(
                "Clone to device",
                "Please open valid icf file or clone data from device.",
            )
            return

        gui_dlg_clone.CloneToRadioDialog(self, self._radio_memory)

    def __on_radio_info(self, _event: tk.Event | None = None) -> None:  # type: ignore
        dlg = gui_dlg_clone.RadioInfoDialog(self)
        if model := dlg.result:
            info = (
                f"Model: {model.human_model()}\n"
                f"Rev: {model.rev}\n"
                f"Is IC-R6: {model.is_icr6()}\n"
                f"Serial: {model.serial}\n"
                f"Comment: {model.comment}"
            )
            messagebox.showinfo("Radio info", info)

    def __on_export(self, what: str) -> None:
        fname = filedialog.asksaveasfilename(
            parent=self,
            filetypes=[("CSV file", ".csv"), ("All files", "*.*")],
            initialdir=str(self._last_file.parent) if self._last_file else ".",
            initialfile=f"{what}.csv",
            defaultextension=".csv",
        )

        if not fname:
            return

        match what:
            case "channels":
                channels = self._radio_memory.get_active_channels()
                expimp.export_channels_file(channels, Path(fname))

            case "awchannels":
                channels = self._radio_memory.get_autowrite_channels()
                expimp.export_awchannels_file(channels, Path(fname))


def start_gui() -> None:
    file = Path(sys.argv[1]) if len(sys.argv) > 1 else None

    root = tk.Tk()
    gui_model.Clipboard.initialize(root)

    root.title("ICOM IC-R6 Tool")
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("pad.TEntry", padding="1 1 1 1")
    myapp = App(root, file)
    root.geometry("1024x768")
    root.wait_visibility()
    root.grab_set()
    root.lift()

    myapp.mainloop()

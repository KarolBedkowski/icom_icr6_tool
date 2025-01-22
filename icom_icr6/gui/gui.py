# Copyright © 2024-2025 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import importlib.resources
import logging
import os
import tkinter as tk
import typing as ty
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from icom_icr6 import VERSION, config, expimp, ic_io, reports
from icom_icr6.change_manager import ChangeManeger
from icom_icr6.radio_memory import RadioMemory

from . import (
    awchannels_page,
    banks_page,
    channels_page,
    dlg_clone,
    dlg_find,
    dlg_reports,
    gui_model,
    scanedges_page,
    scanlinks_page,
    settings_page,
)

_LOG = logging.getLogger(__name__)


@ty.runtime_checkable
class TabWidget(ty.Protocol):
    def update_tab(self) -> None: ...
    def reset(self) -> None: ...


class App(tk.Frame):
    def __init__(self, master: tk.Tk, file: Path | None) -> None:
        super().__init__(master)
        self.master = master

        self._last_file: Path | None = None
        self._radio_memory = self._load_default_icf()
        self._change_manager = ChangeManeger(self._radio_memory)
        self._change_manager.on_undo_changes = self._on_undo_change
        # safe is clone to device when data are loaded or cloned from radio
        self._safe_for_clone = False

        # variable for window status bar
        self._status_value = tk.StringVar()

        self.pack(fill="both", expand=1)

        self._create_menu(master)

        self._ntb = ttk.Notebook(self)
        self._ntb.add(self._create_nb_channels(), text="Channels")
        self._ntb.add(self._create_nb_banks(), text="Banks")
        self._ntb.add(self._create_nb_scan_edge(), text="Scan Edge")
        self._ntb.add(self._create_nb_scan_links(), text="Scan Link")
        self._ntb.add(self._create_nb_awchannels(), text="Autowrite channels")
        self._ntb.add(self._create_nb_settings(), text="Settings")
        self._ntb.bind("<<NotebookTabChanged>>", self.__on_nb_page_changed)

        self._pages: tuple[TabWidget, ...] = (
            self._nb_channels,
            self._nb_banks,
            self._nb_scan_edge,
            self._nb_scan_links,
            self._nb_aw_channels,
            self._nb_settings,
        )

        self._ntb.pack(fill="both", expand=True)

        tk.Label(self, text="", textvariable=self._status_value).pack(
            side=tk.LEFT,
            fill=tk.X,
        )

        if file:
            self._load_icf(file)
        else:
            self._set_loaded_filename(None)

        self.bind("<Destroy>", self.__on_destroy)
        master.protocol("WM_DELETE_WINDOW", self.__on_closing)

    def set_status(self, msg: str) -> None:
        """Set status panel content."""
        self._status_value.set(msg)

    ## properties

    @property
    def _selected_tab(self) -> int:
        try:
            return self._ntb.tabs().index(self._ntb.select())  # type: ignore
        except ValueError:
            return 0

    # create objects

    def _create_menu(self, master: tk.Tk) -> None:
        menu_bar = tk.Menu(master, tearoff=False)
        master.config(menu=menu_bar)

        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(
            label="New...",
            command=self._on_menu_file_new,
            accelerator="Ctrl+N",
        )
        file_menu.add_command(
            label="Open...",
            command=self._on_menu_file_open,
            accelerator="Ctrl+O",
        )
        master.bind_all("<Control-o>", self._on_menu_file_open)
        file_menu.add_command(
            label="Save...",
            command=self._on_menu_file_save,
            accelerator="Ctrl+S",
        )
        master.bind_all("<Control-s>", self._on_menu_file_save)
        file_menu.add_command(
            label="Save As...",
            command=self._on_menu_file_save_as,
            accelerator="Shift+Ctrl+S",
        )
        master.bind_all("<Shift-Control-s>", self._on_menu_file_save_as)

        self._last_files_menu = tk.Menu(file_menu, tearoff=False)
        self._fill_menu_last_files()
        file_menu.add_cascade(
            label="Last files...", menu=self._last_files_menu
        )

        file_menu.add_separator()

        export_menu = self._create_menu_export(file_menu)
        file_menu.add_cascade(label="Export...", menu=export_menu)

        file_menu.add_separator()

        file_menu.add_command(label="Exit", command=self.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)

        self.__menu_edit = edit_menu = tk.Menu(menu_bar, tearoff=False)
        edit_menu.add_command(
            label="Undo",
            command=self._on_menu_undo,
            accelerator="Ctrl+Z",
        )
        master.bind_all("<Control-z>", self._on_menu_undo)
        edit_menu.add_command(
            label="Redo",
            command=self._on_menu_redo,
            accelerator="Ctrl+Y",
        )
        master.bind_all("<Control-y>", self._on_menu_redo)

        edit_menu.add_separator()

        edit_menu.add_command(
            label="Find...",
            command=self._on_menu_find,
            accelerator="Ctrl+F",
        )
        master.bind_all("<Control-f>", self._on_menu_find)

        edit_menu.add_separator()

        edit_menu.add_command(
            label="Reports...", command=self._on_menu_reports
        )

        menu_bar.add_cascade(label="Edit", menu=edit_menu)

        radio_menu = tk.Menu(menu_bar, tearoff=False)
        radio_menu.add_command(
            label="Clone from radio...", command=self._on_menu_clone_from_radio
        )
        radio_menu.add_command(
            label="Clone to radio...", command=self._on_menu_clone_to_radio
        )
        radio_menu.add_command(
            label="Info...", command=self._on_menu_radio_info
        )
        menu_bar.add_cascade(label="Radio", menu=radio_menu)

        help_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu.add_command(label="About", command=self._on_menu_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)

    def _create_menu_export(self, parent: tk.Menu) -> tk.Menu:
        menu = tk.Menu(parent, tearoff=False)
        menu.add_command(
            label="Channels...",
            command=lambda: self._on_menu_export("channels"),
        )
        menu.add_command(
            label="Autowrrite channels...",
            command=lambda: self._on_menu_export("awchannels"),
        )
        menu.add_command(label="Sheet...", command=self._on_menu_export_sheet)
        return menu

    def _create_nb_channels(self) -> tk.Widget:
        self._nb_channels = channels_page.ChannelsPage(
            self, self._change_manager
        )
        return self._nb_channels

    def _create_nb_banks(self) -> tk.Widget:
        self._nb_banks = banks_page.BanksPage(self, self._change_manager)
        return self._nb_banks

    def _create_nb_scan_edge(self) -> tk.Frame:
        self._nb_scan_edge = scanedges_page.ScanEdgesPage(
            self, self._change_manager
        )
        return self._nb_scan_edge

    def _create_nb_scan_links(self) -> tk.Widget:
        self._nb_scan_links = scanlinks_page.ScanLinksPage(
            self, self._change_manager
        )
        return self._nb_scan_links

    def _create_nb_awchannels(self) -> tk.Widget:
        self._nb_aw_channels = awchannels_page.AutoWriteChannelsPage(
            self, self._change_manager
        )
        return self._nb_aw_channels

    def _create_nb_settings(self) -> tk.Widget:
        self._nb_settings = settings_page.SettingsPage(
            self, self._change_manager
        )
        return self._nb_settings

    # menu callbacks

    def _on_menu_about(self) -> None:
        messagebox.showinfo(
            "About",
            f"Icom IC-R6 tool\nVersion: {VERSION}\n\n"
            "Future information in README.rst, COPYING files.",
        )

    def _on_menu_file_new(self, _event: tk.Event | None = None) -> None:  # type: ignore
        mem = self._load_default_icf()
        self._radio_memory.update_from(mem)
        self._set_loaded_filename(None)
        self._update_tab_content()
        self.set_status("Loaded default file")
        self._safe_for_clone = True
        self._change_manager.reset()

    def _on_menu_file_open(self, _event: tk.Event | None = None) -> None:  # type: ignore
        fname = filedialog.askopenfilename(
            parent=self,
            filetypes=[("Supported files", ".icf"), ("All files", "*.*")],
            initialdir=str(self._last_file.parent) if self._last_file else ".",
            defaultextension=".icf",
        )

        if fname:
            self._load_icf(Path(fname))

    def _on_menu_file_save(self, _event: tk.Event | None = None) -> None:  # type: ignore
        if not self._last_file:
            self._on_menu_file_save_as()
            return

        try:
            self._radio_memory.validate_loaded_data()
        except ValueError as err:
            messagebox.showerror("Save file error - Invalid data", str(err))
            return

        try:
            ic_io.save_icf_file(self._last_file, self._radio_memory)
        except Exception as err:
            _LOG.exception("_on_menu_file_save_as error")
            messagebox.showerror("Save file error", str(err))
            return

        self._change_manager.reset_changes_cnt()
        self.set_status(f"File {self._last_file} saved")
        self._update_window_title()

    def _on_menu_file_save_as(self, _event: tk.Event | None = None) -> None:  # type: ignore
        try:
            self._radio_memory.validate_loaded_data()
        except ValueError as err:
            messagebox.showerror("Save file error - Invalid data", str(err))
            return

        fname = filedialog.asksaveasfilename(
            parent=self,
            filetypes=[("Supported files", ".icf"), ("All files", "*.*")],
            initialdir=str(self._last_file.parent) if self._last_file else ".",
            initialfile=self._last_file.name if self._last_file else "",
            defaultextension=".icf",
        )

        if fname:
            try:
                ic_io.save_icf_file(Path(fname), self._radio_memory)
            except Exception as err:
                _LOG.exception("_on_menu_file_save_as error")
                messagebox.showerror("Save file error", str(err))
                return

            self._change_manager.reset_changes_cnt()
            self._set_loaded_filename(Path(fname))
            self.set_status(f"File {fname} saved")

    def _on_menu_undo(self, _event: tk.Event | None = None) -> None:  # type: ignore
        _LOG.info("_on_menu_undo")
        if self._change_manager.undo():
            self._update_tab_content()

        _LOG.info("_on_menu_undo finished")

    def _on_menu_redo(self, _event: tk.Event | None = None) -> None:  # type: ignore
        if self._change_manager.redo():
            self._update_tab_content()

    def _on_menu_find(self, _event: tk.Event | None = None) -> None:  # type: ignore
        dlg_find.FindDialog(
            self, self._radio_memory, self._on_find_object_select
        )

    def _on_menu_reports(self, _event: tk.Event | None = None) -> None:  # type: ignore
        dlg_reports.ReportsDialog(self, self._radio_memory)

    def __on_nb_page_changed(self, _event: tk.Event) -> None:  # type: ignore
        self.set_status("")
        self._update_tab_content()

    def _on_menu_clone_from_radio(
        self,
        _event: tk.Event | None = None,  # type: ignore
    ) -> None:
        dlg = dlg_clone.CloneFromRadioDialog(self)
        if dlg.radio_memory:
            mem = dlg.radio_memory
            try:
                mem.validate()
            except ValueError as err:
                messagebox.showerror(
                    "Clone from radio error",
                    f"Cloned data is invalid: {err}",
                )
                return

            self._radio_memory.update_from(mem)
            self._safe_for_clone = True
            self._set_loaded_filename(None)
            self._reset_tab_content()
            self._change_manager.reset()

    def _on_menu_clone_to_radio(self, _event: tk.Event | None = None) -> None:  # type: ignore
        if not self._safe_for_clone and not messagebox.askokcancel(
            "Clone to device",
            "Clone default data (for global region) to radio may don't "
            "work as expected. \n"
            "For safe operation please open valid icf file or clone data "
            "from device.\n\n"
            "Continue?",
        ):
            return

        try:
            self._radio_memory.validate_loaded_data()
            self._radio_memory.commit()
        except ValueError as err:
            messagebox.showerror("Clone to device - Invalid data", str(err))
            return

        dlg_clone.CloneToRadioDialog(self, self._radio_memory)

    def _on_menu_radio_info(self, _event: tk.Event | None = None) -> None:  # type: ignore
        dlg = dlg_clone.RadioInfoDialog(self)
        if model := dlg.result:
            info = (
                f"Model: {model.human_model()}\n"
                f"Rev: {model.rev}\n"
                f"Is IC-R6: {'yes' if model.is_icr6() else 'no'}\n"
                f"Serial: {model.serial}\n"
                f"Comment: {model.comment}"
            )
            messagebox.showinfo("Radio info", info)

    def _on_menu_export(self, what: str) -> None:
        fname = filedialog.asksaveasfilename(
            parent=self,
            filetypes=[("CSV file", ".csv"), ("All files", "*.*")],
            initialdir=str(self._last_file.parent) if self._last_file else ".",
            initialfile=f"{what}.csv",
            defaultextension=".csv",
        )
        if not fname:
            return

        dstfile = Path(fname)

        try:
            match what:
                case "channels":
                    channels = self._radio_memory.get_active_channels()
                    expimp.export_channels_file(channels, dstfile)

                case "awchannels":
                    channels = self._radio_memory.awchannels
                    expimp.export_awchannels_file(channels, dstfile)

        except Exception as err:
            messagebox.showerror("Export error", str(err))
            return

    def _on_menu_export_sheet(self) -> None:
        fname = filedialog.asksaveasfilename(
            parent=self,
            filetypes=[("TXT file", ".txt"), ("All files", "*.*")],
            initialdir=str(self._last_file.parent) if self._last_file else ".",
            initialfile="sheet.txt",
            defaultextension=".txt",
        )
        if not fname:
            return

        dstfile = Path(fname)

        try:
            with dstfile.open(mode="wt", encoding="UTF-8") as ofile:
                for line in reports.generate_sheet(self._radio_memory):
                    ofile.write(line)
                    ofile.write("\n")

        except Exception as err:
            messagebox.showerror("Export error", str(err))
            return

    def _on_undo_change(self, has_undo: bool, has_redo: bool) -> None:  # noqa:FBT001
        """Callback for changes in undo queue."""
        self.__menu_edit.entryconfigure(
            "Undo", state="normal" if has_undo else tk.DISABLED
        )
        self.__menu_edit.entryconfigure(
            "Redo", state="normal" if has_redo else tk.DISABLED
        )
        self._update_window_title()

    def _on_find_object_select(self, kind: str, index: object) -> None:
        """Object clicked in find dialog."""
        match kind:
            case "channel":
                assert isinstance(index, int)
                if self._switch_to_tab(0):
                    self._nb_channels.update_tab(index)
                else:
                    self._nb_channels.select(index)

            case "bank_pos":
                assert isinstance(index, tuple)
                bank, bank_pos = index

                if self._switch_to_tab(1):
                    self._nb_banks.update_tab(bank, bank_pos)
                else:
                    self._nb_banks.select(bank, bank_pos)

            case "awchannel":
                assert isinstance(index, int)
                if self._switch_to_tab(4):
                    self._nb_aw_channels.update_tab(index)
                else:
                    self._nb_aw_channels.select(index)

    def _on_menu_last_file(self, fname: str) -> None:
        """Callback for last file menu item."""
        self._load_icf(Path(fname))

    ##  window callbacks

    def __on_closing(self) -> None:
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.master.destroy()

    def __on_destroy(self, _event: tk.Event) -> None:  # type: ignore
        """Save window geometry."""
        config.CONFIG.main_window_geometry = self.master.geometry()  # type: ignore

    ## actions

    def _switch_to_tab(self, index: int) -> bool:
        """Switch main notebook to `index` tab. Return True when switched,
        False when already `index` tab is visible."""
        ntb = self._ntb
        tabs = ntb.tabs()
        selected_tab = tabs.index(ntb.select())
        if selected_tab == index:
            return False

        ntb.select(tabs[index])
        return True

    def _set_loaded_filename(self, fname: Path | None) -> None:
        if fname:
            config.CONFIG.push_last_file(str(fname.resolve()))
            self._fill_menu_last_files()

        self._last_file = fname
        self._update_window_title()

    def _update_window_title(self) -> None:
        fname = self._last_file
        title = f" [{fname.name}]" if fname else ""
        if self._change_manager.changed:
            title += " [+]"

        self.master.title(f"ICOM IC-R6 Tool{title}")  # type: ignore

    def _update_tab_content(self) -> None:
        selected_tab = self._selected_tab
        _LOG.debug("update page: %r", selected_tab)
        self._pages[selected_tab].update_tab()

    def _reset_tab_content(self) -> None:
        for page in self._pages:
            page.reset()

    def _load_default_icf(self) -> RadioMemory:
        with importlib.resources.path(
            "icom_icr6.data", "default_global.icf"
        ) as icf_file:
            return ic_io.load_icf_file(icf_file)

    def _load_icf(self, file: Path) -> None:
        try:
            mem = ic_io.load_icf_file(file)
            mem.validate()
            self._radio_memory.update_from(mem)

        except ValueError as err:
            messagebox.showerror(
                "Load file error", f"Loaded data are invalid: {err}"
            )

        except Exception as err:
            messagebox.showerror("Load file error", f"Load error: {err}")
            return

        self._set_loaded_filename(file)
        self._reset_tab_content()
        self.set_status(f"File {file} loaded")
        self._safe_for_clone = True
        self._change_manager.reset()

    def _fill_menu_last_files(self) -> None:
        """Fill menu file -> last files."""
        menu = self._last_files_menu
        if num_elements := menu.index(tk.END):
            menu.delete(0, num_elements)

        for fname in config.CONFIG.last_files:

            def command(name: str = fname) -> None:
                self._on_menu_last_file(name)

            menu.add_command(label=fname, command=command)


def start_gui(cfg_file: Path | None, icf_file: Path | None) -> None:
    config_path = cfg_file or config.default_config_path()
    config.load(config_path)

    root = tk.Tk()
    gui_model.Clipboard.initialize(root)

    # set scaling; my help for hdpi displays
    scaling = config.CONFIG.gui_scaling
    if not scaling:
        try:
            scaling = float(os.environ["GDK_SCALE"])
        except ValueError:
            _LOG.warning("invalid env GDK_SCALE")
        except KeyError:
            pass

    if scaling:
        _LOG.info("set scale: %r", scaling)
        root.tk.call("tk", "scaling", scaling)

    root.title("ICOM IC-R6 Tool")
    style = ttk.Style()
    style.theme_use("clam")
    myapp = App(root, icf_file)
    root.geometry(config.CONFIG.main_window_geometry)
    root.wait_visibility()
    root.lift()

    myapp.mainloop()
    config.save(config_path)

# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import sys
import tkinter as tk
import typing as ty
from pathlib import Path
from tkinter import filedialog, ttk

from . import gui_model, gui_nb_channels, io, model
from .gui_model import yes_no
from .gui_widgets import build_list


class App(tk.Frame):
    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master)

        self._last_dir = Path()
        self._radio_memory = model.RadioMemory()
        self._channel_model = gui_model.ChannelModel()

        self.pack(fill="both", expand=1)

        self.__create_menu(master)

        self._ntb = ttk.Notebook(self)
        self._ntb.add(self.__create_nb_channels(), text="Channels")
        self._ntb.add(self.__create_nb_banks(), text="Banks")
        self._ntb.add(self.__create_nb_scan_edge(), text="Scan Edge")
        self._ntb.add(self.__create_nb_scan_links(), text="Scan Link")

        self._ntb.pack(fill="both", expand=1)

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

    def __create_nb_banks(self) -> ttk.PanedWindow:
        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        banks = self._banks = tk.Listbox(pw, selectmode=tk.SINGLE)
        self.__fill_banks()

        banks.bind("<<ListboxSelect>>", self.__fill_bank)
        pw.add(banks, weight=0)

        columns = [
            ("num", "Num", tk.E, 30),
            ("chn", "Chn", tk.E, 30),
            ("freq", "freq", tk.E, 30),
            ("name", "name", tk.W, 30),
            ("ts", "ts", tk.CENTER, 30),
            ("mode", "mode", tk.CENTER, 30),
            ("af", "af", tk.CENTER, 30),
            ("att", "att", tk.CENTER, 30),
            ("vsc", "vsc", tk.CENTER, 30),
            ("skip", "skip", tk.CENTER, 30),
        ]
        frame, self._bank_content = build_list(pw, columns)
        pw.add(frame, weight=1)

        return pw

    def __create_nb_scan_edge(self) -> tk.Frame:
        columns = [
            ("no", "No", tk.E, 30),
            ("name", "name", tk.W, 30),
            ("start", "Start", tk.E, 30),
            ("end", "End", tk.E, 30),
            ("ts", "TS", tk.CENTER, 30),
            ("mode", "Mode", tk.CENTER, 30),
            ("att", "ATT", tk.CENTER, 30),
        ]
        frame, self._scan_edges = build_list(self, columns)
        return frame

    def __create_nb_scan_links(self) -> ttk.PanedWindow:
        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        sl = self._scan_links = tk.Listbox(pw, selectmode=tk.SINGLE)
        self.__fill_scan_links()

        sl.bind("<<ListboxSelect>>", self.__fill_scan_link)
        pw.add(sl, weight=0)

        self._scan_links_edges = tk.Listbox(pw, selectmode=tk.MULTIPLE)
        pw.add(self._scan_links_edges, weight=1)

        return pw

    def __about_handler(self) -> None:
        pass

    def __file_open_handler(self) -> None:
        fname = filedialog.askopenfilename(
            parent=self,
            filetypes=[("Supported files", ".icf"), ("All files", "*.*")],
            initialdir=str(self._last_dir),
        )

        if fname:
            self.load_icf(Path(fname))

        self.focus_set()

    def load_icf(self, file: Path) -> None:
        self._radio_memory = io.load_icf_file(file)
        self._last_dir = file.parent
        self.__fill_widgets()

    def __file_save_handler(self) -> None:
        pass

    def __fill_widgets(self) -> None:
        self._nb_channels.set(self._radio_memory)
        self.__fill_banks()
        self._banks.selection_set(0)
        self._banks.activate(0)
        self.__fill_scan_edges()
        self.__fill_scan_links()

    def __fill_banks(self) -> None:
        banks = self._banks
        banks.delete(0, banks.size())
        for idx, bname in enumerate(model.BANK_NAMES):
            bank = self._radio_memory.get_bank(idx)
            name = f"{bname}: {bank.name}" if bank.name else bname
            banks.insert(tk.END, name)

    def __fill_bank(self, _event: tk.Event) -> None:
        selected_bank = 0
        if sel := self._banks.curselection():  # type: ignore
            selected_bank = sel[0]

        bcont = self._bank_content
        bcont.delete(*bcont.get_children())

        bank = self._radio_memory.get_bank(selected_bank)

        for idx, channel in enumerate(bank.channels):
            if not channel or channel.hide_channel or not channel.freq:
                bcont.insert(
                    parent="",
                    index=tk.END,
                    iid=idx,
                    text="",
                    values=(str(idx), "", "", "", "", "", "", "", "", ""),
                )
                continue

            bcont.insert(
                parent="",
                index=tk.END,
                iid=idx,
                text="",
                values=(
                    str(idx),
                    str(channel.number),
                    str(channel.freq // 1000),
                    channel.name,
                    model.STEPS[channel.tuning_step],
                    model.MODES[channel.mode],
                    yes_no(channel.af_filter),
                    yes_no(channel.attenuator),
                    yes_no(channel.vsc),
                    model.SKIPS[channel.skip],
                ),
            )

        bcont.yview(0)
        bcont.xview(0)

    def __fill_scan_edges(self) -> None:
        tree = self._scan_edges
        tree.delete(*tree.get_children())

        for idx in range(24):
            se = self._radio_memory.get_scan_edge(idx)
            if se.disabled or not se.start:
                tree.insert(
                    parent="",
                    index=tk.END,
                    iid=idx,
                    text="",
                    values=(str(idx), "", "", "", "", "", ""),
                )
                continue

            tree.insert(
                parent="",
                index=tk.END,
                iid=idx,
                text="",
                values=(
                    str(idx),
                    se.name,
                    str(se.start // 1000),
                    str(se.end // 1000),
                    model.STEPS[se.ts],
                    model.MODES[se.mode],
                    se.human_attn(),
                ),
            )

        tree.yview(0)
        tree.xview(0)

    def __fill_scan_links(self) -> None:
        sls = self._scan_links
        sls.delete(0, sls.size())
        for idx in range(10):
            sl = self._radio_memory.get_scan_link(idx)
            name = f"{idx}: {sl.name}" if sl.name else str(idx)
            sls.insert(tk.END, name)

    def __fill_scan_link(self, event: tk.Event) -> None:
        sel_sl = self._scan_links.curselection()
        if not sel_sl:
            return

        slse = self._scan_links_edges
        slse.delete(0, slse.size())
        for idx in range(25):
            se = self._radio_memory.get_scan_edge(idx)
            if se.start:
                sename = se.name or "-"
                name = f"{idx}: {sename} {se.start} - {se.end} / {se.mode}"
            else:
                name = str(idx)

            slse.insert(tk.END, name)

        sl = self._radio_memory.get_scan_link(sel_sl[0])
        for edge in sl.edges:
            slse.selection_set(edge)


def start_gui() -> None:
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use("clam")
    myapp = App(root)
    root.geometry("1024x768")
    root.lift()

    if len(sys.argv) > 1:
        myapp.load_icf(Path(sys.argv[1]))

    myapp.mainloop()

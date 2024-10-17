# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import typing as ty

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import io, model


class App(tk.Frame):
    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master)

        self._last_dir = Path()
        self._radio_memory = model.RadioMemory()

        self.pack(fill="both", expand=1)

        self.__create_menu(master)

        self._ntb = ttk.Notebook(self)
        self._ntb.add(self.__create_nb_channels(), text="Channels")
        self._ntb.add(self.__create_nb_banks(), text="Banks")
        self._ntb.add(self.__create_nb_scan_edge(), text="Scan Edge")

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

    def __create_nb_channels(self) -> ttk.PanedWindow:
        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self._channel_ranges = tk.Listbox(pw, selectmode=tk.SINGLE)
        self._channel_ranges.insert(
            tk.END,
            "0-99",
            "100-199",
            "200-299",
            "300-399",
            "400-499",
            "500-599",
            "600-699",
            "700-799",
            "800-899",
            "900-999",
            "1000-1099",
            "1100-1199",
            "1200-1299",
        )
        pw.add(self._channel_ranges, weight=0)
        self._channel_ranges.bind("<<ListboxSelect>>", self.__fill_channels)

        columns = (
            ("num", "Num", tk.E, 30),
            ("freq", "Freq", tk.E, 80),
            ("name", "Name", tk.W, 50),
            ("af", "AF", tk.CENTER, 25),
            ("att", "ATT", tk.CENTER, 25),
            ("mode", "Mode", tk.CENTER, 25),
            ("ts", "TS", tk.CENTER, 25),
            ("vsc", "VSC", tk.CENTER, 25),
            ("skip", "Skip", tk.CENTER, 25),
            ("bank", "Bank", tk.W, 25),
        )
        frame, self._channels_content = _build_list(pw, columns)
        pw.add(frame, weight=1)

        return pw

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
        frame, self._bank_content = _build_list(pw, columns)
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
        frame, self._scan_edges = _build_list(self, columns)
        return frame

    def __about_handler(self) -> None:
        pass

    def __file_open_handler(self) -> None:
        fname = filedialog.askopenfilename(
            parent=self,
            filetypes=[("Supported files", ".icf"), ("All files", "*.*")],
            initialdir=str(self._last_dir),
        )

        if fname:
            file = Path(fname)
            self._radio_memory = io.load_icf_file(file)
            self._last_dir = file.parent
            self.__fill_widgets()

        self.focus_set()

    def __file_save_handler(self) -> None:
        pass

    def __fill_widgets(self) -> None:
        self._channel_ranges.selection_set(0)
        self._channel_ranges.activate(0)
        self.__fill_banks()
        self._banks.selection_set(0)
        self._banks.activate(0)
        self.__fill_scan_edges()

    def __fill_channels(self, _event: tk.Event) -> None:
        selected_range = 0
        if sel := self._channel_ranges.curselection():
            selected_range = sel[0]

        self._channels_content.delete(*self._channels_content.get_children())

        range_start = selected_range * 100
        for idx in range(range_start, range_start + 100):
            channel = self._radio_memory.get_channel(idx)
            if channel.hide_channel or not channel.freq:
                self._channels_content.insert(
                    parent="",
                    index=tk.END,
                    iid=idx,
                    text="",
                    values=(str(idx), "", "", "", "", "", "", "", "", ""),
                )
                continue

            try:
                bank = f"{model.BANK_NAMES[channel.bank]} {channel.bank_pos}"
            except IndexError:
                bank = ""

            self._channels_content.insert(
                parent="",
                index=tk.END,
                iid=idx,
                text="",
                values=(
                    str(idx),
                    str(channel.freq),
                    channel.name,
                    _yes_no(channel.af_filter),
                    _yes_no(channel.attenuator),
                    model.MODES[channel.mode],
                    model.STEPS[channel.tuning_step],
                    _yes_no(channel.vsc),
                    model.SKIPS[channel.skip],
                    bank,
                ),
            )

        self._channels_content.yview(0)
        self._channels_content.xview(0)

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
                    str(channel.freq),
                    channel.name,
                    model.STEPS[channel.tuning_step],
                    model.MODES[channel.mode],
                    _yes_no(channel.af_filter),
                    _yes_no(channel.attenuator),
                    _yes_no(channel.vsc),
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
                    str(se.start),
                    str(se.end),
                    model.STEPS[se.ts],
                    model.MODES[se.mode],
                    se.human_attn(),
                ),
            )

        tree.yview(0)
        tree.xview(0)

def _build_list(
    parent: tk.Widget, columns: ty.Iterable[tuple[str, str, str, int]]
) -> tuple[tk.Frame, ttk.Treeview]:
    frame = tk.Frame(parent)
    vert_scrollbar = ttk.Scrollbar(frame, orient="vertical")
    vert_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    hor_scrollbar = ttk.Scrollbar(frame, orient="horizontal")
    hor_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

    col_ids = [c[0] for c in columns]
    tree = ttk.Treeview(frame, columns=col_ids)
    tree.column("#0", width=0, stretch=tk.NO)
    for col_id, title, anchor, width in columns:
        tree.column(col_id, anchor=anchor, width=width)
        tree.heading(col_id, text=title, anchor=tk.CENTER)

    tree.pack(fill=tk.BOTH, expand=True)
    vert_scrollbar.config(command=tree.yview)
    hor_scrollbar.config(command=tree.xview)
    tree.configure(
        yscrollcommand=vert_scrollbar.set, xscrollcommand=hor_scrollbar.set
    )

    return frame, tree


def _yes_no(value: bool | None) -> str:
    match value:
        case None:
            return ""
        case True:
            return "yes"
        case False:
            return "no"


def start_gui() -> None:
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use("clam")
    myapp = App(root)
    root.geometry("1024x768")
    root.lift()
    myapp.mainloop()

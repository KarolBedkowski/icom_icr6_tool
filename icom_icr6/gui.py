# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import io, model


class App(tk.Frame):
    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master)

        self._last_dir = Path(".")
        self._radio_memory = model.RadioMemory()

        self.pack(fill="both", expand=1)

        self.__create_menu(master)

        self._ntb = ttk.Notebook(self)
        self._ntb.add(self.__create_nb_channels(), text="Channels")

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
        columns=(
                "num",
                "freq",
                "name",
                "af",
                "att",
                "mode",
                "ts",
                "vsc",
                "skip",
                "bank",
            )
        self._channels_content = ttk.Treeview(
            pw,
            columns=columns,
        )
        self._channels_content.column("#0", width=0,  stretch=tk.NO)
        self._channels_content.column("num",anchor=tk.E, width=40)
        self._channels_content.column("freq",anchor=tk.E, width=80)
        self._channels_content.column("name",anchor=tk.W, width=50)
        self._channels_content.column("af",anchor=tk.CENTER, width=50)
        self._channels_content.column("att",anchor=tk.CENTER, width=50)
        self._channels_content.column("mode",anchor=tk.CENTER, width=50)
        self._channels_content.column("ts",anchor=tk.CENTER, width=50)
        self._channels_content.column("vsc",anchor=tk.CENTER, width=50)
        self._channels_content.column("skip",anchor=tk.CENTER, width=50)
        self._channels_content.column("bank",anchor=tk.CENTER, width=50)

        for c in columns:
            self._channels_content.heading(c,text=c,anchor=tk.CENTER)

        pw.add(self._channels_content, weight=1)


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
            file = Path(fname)
            self._radio_memory = io.load_icf_file(file)
            self._last_dir = file.parent

        self.focus_set()

    def __file_save_handler(self) -> None:
        pass

    def __fill_widgets(self) -> None:
        self._channel_ranges.activate(0)
        pass

    def __fill_channels(self, event) -> None:
        ic(event)
        selected_range = 0
        if sel := self._channel_ranges.curselection():
            selected_range = sel[0]

        self._channels_content.delete(*self._channels_content.get_children())

        range_start = selected_range * 100
        for idx in range(range_start, range_start + 100):
            channel = self._radio_memory.get_channel(idx)
            if channel.hide_channel:
                self._channels_content.insert(
                    parent="", index=tk.END, iid=idx, text=""
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


def _yes_no(value: bool|None) -> str:
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

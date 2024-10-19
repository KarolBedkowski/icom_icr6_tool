# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import sys
import tkinter as tk
import typing as ty
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import io, model


class _ChannelModel:
    def __init__(self) -> None:
        self.number = 0
        self.freq = tk.IntVar()
        self.name = tk.StringVar()
        self.mode = tk.StringVar()
        self.ts = tk.StringVar()
        self.af = tk.IntVar()
        self.attn = tk.IntVar()
        self.vsc = tk.IntVar()
        self.skip = tk.StringVar()

        self.duplex = tk.StringVar()
        self.offset = tk.IntVar()
        self.tmode = tk.StringVar()
        self.ctone = tk.StringVar()
        self.dtsc = tk.StringVar()
        self.polarity = tk.StringVar()

        self.bank = tk.StringVar()
        self.bank_pos = tk.IntVar()

    def fill(self, chan: model.Channel) -> None:
        ic(chan)
        self.number = chan.number
        if chan.hide_channel:
            self.name.set("")
            self.freq.set(0)
            self.mode.set("")
            self.ts.set("")
            self.af.set(0)
            self.attn.set(0)
            self.vsc.set(0)
            self.skip.set("")
            self.duplex.set("")
            self.offset.set(0)
            self.tmode.set("")
            self.ctone.set("")
            self.dtsc.set("")
            self.polarity.set("")
            self.bank.set("")
            self.bank_pos.set(0)
            return

        self.name.set(chan.name)
        self.freq.set(chan.freq)
        self.mode.set(model.MODES[chan.mode])
        self.ts.set(str(model.STEPS[chan.tuning_step]))
        self.af.set(1 if chan.af_filter else 0)
        self.attn.set(1 if chan.attenuator else 0)
        self.vsc.set(1 if chan.vsc else 0)
        self.skip.set(model.SKIPS[chan.skip])
        try:
            self.duplex.set(model.DUPLEX_DIRS[chan.duplex])
        except IndexError:
            self.duplex.set("")
        self.offset.set(chan.offset)
        try:
            self.tmode.set(model.TONE_MODES[chan.tmode])
        except IndexError:
            self.tmode.set("")
        try:
            self.ctone.set(model.CTCSS_TONES[chan.ctone])
        except IndexError:
            self.ctone.set("")
        try:
            self.dtsc.set(model.DTCS_CODES[chan.dtsc])
        except IndexError:
            self.dtsc.set("")
        try:
            self.polarity.set(model.POLARITY[chan.polarity])
        except IndexError:
            self.polarity.set("")
        try:
            self.bank.set(model.BANK_NAMES[chan.bank])
            self.bank_pos.set(chan.bank_pos)
        except IndexError:
            self.bank.set("")
            self.bank_pos.set(0)


class App(tk.Frame):
    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master)

        self._last_dir = Path()
        self._radio_memory = model.RadioMemory()
        self._channel_model = _ChannelModel()

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

        frame = tk.Frame(pw)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(1, weight=0)
        frame.columnconfigure(0, weight=1)

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
        ccframe, self._channels_content = _build_list(frame, columns)
        ccframe.grid(
            row=0, column=0, sticky=tk.N + tk.S + tk.E + tk.W, padx=6, pady=6
        )
        self._channels_content.bind(
            "<<TreeviewSelect>>", self.__on_channel_select
        )

        fields_frame = tk.Frame(frame)
        fields_frame.columnconfigure(0, weight=0)
        fields_frame.columnconfigure(1, weight=1)
        fields_frame.columnconfigure(2, weight=0)
        fields_frame.columnconfigure(3, weight=1)
        fields_frame.columnconfigure(4, weight=0)
        fields_frame.columnconfigure(5, weight=1)
        fields_frame.columnconfigure(6, weight=0)
        fields_frame.columnconfigure(7, weight=1)

        def create_entry(
            row: int, col: int, label: str, var: tk.Variable
        ) -> None:
            tk.Label(fields_frame, text=label).grid(
                row=row, column=col, sticky=tk.N + tk.W, padx=6, pady=6
            )
            ttk.Entry(fields_frame, textvariable=var).grid(
                row=row,
                column=col + 1,
                sticky=tk.N + tk.W + tk.E,
                padx=6,
                pady=6,
            )

        def create_combo(
            row: int, col: int, label: str, var: tk.Variable, values: list[str]
        ) -> None:
            tk.Label(fields_frame, text=label).grid(
                row=row, column=col, sticky=tk.N + tk.W, padx=6, pady=6
            )
            ttk.Combobox(
                fields_frame,
                values=values,
                exportselection=False,
                state="readonly",
                textvariable=var,
            ).grid(
                row=row,
                column=col + 1,
                sticky=tk.N + tk.W + tk.E,
                padx=6,
                pady=6,
            )

        def create_check(
            row: int, col: int, label: str, var: tk.Variable
        ) -> None:
            tk.Checkbutton(
                fields_frame,
                text=label,
                variable=var,
                onvalue=1,
                offvalue=0,
            ).grid(row=row, column=col, sticky=tk.N + tk.W + tk.S)

        create_entry(0, 0, "Frequency: ", self._channel_model.freq)
        create_entry(0, 2, "Name: ", self._channel_model.name)
        create_combo(
            0, 4, "Mode: ", self._channel_model.mode, [" ", *model.MODES]
        )
        create_combo(
            0, 6, "TS: ", self._channel_model.ts, list(map(str, model.STEPS))
        )

        create_combo(
            1, 0, "Duplex: ", self._channel_model.duplex, model.DUPLEX_DIRS
        )
        create_entry(1, 2, "Offset: ", self._channel_model.offset)

        create_combo(1, 4, "Skip: ", self._channel_model.skip, model.SKIPS)
        create_check(1, 6, " AF Filter", self._channel_model.af)
        create_check(1, 7, " Attenuator", self._channel_model.attn)

        create_combo(
            2, 0, "Tone: ", self._channel_model.tmode, model.TONE_MODES
        )
        create_combo(
            2,
            2,
            "TSQL: ",
            self._channel_model.ctone,
            list(model.CTCSS_TONES),
        )
        create_combo(
            2, 4, "DTSC: ", self._channel_model.dtsc, model.DTCS_CODES
        )
        create_combo(
            2, 6, "Polarity: ", self._channel_model.polarity, model.POLARITY
        )

        create_check(3, 0, " VSV", self._channel_model.vsc)
        create_combo(
            3, 2, "Bank: ", self._channel_model.bank, [" ", *model.BANK_NAMES]
        )
        create_entry(3, 4, "Bank pos: ", self._channel_model.bank_pos)

        fields_frame.grid(row=1, column=0, sticky=tk.N + tk.S + tk.E + tk.W)

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
        self._channel_ranges.selection_set(0)
        self._channel_ranges.activate(0)
        self.__fill_banks()
        self._banks.selection_set(0)
        self._banks.activate(0)
        self.__fill_scan_edges()
        self.__fill_scan_links()

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
                    str(channel.freq // 1000),
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
                    str(channel.freq // 1000),
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

    def __on_channel_select(self, event: tk.Event) -> None:
        sel = self._channels_content.selection()
        if not sel:
            return

        chan_num = int(sel[0])
        chan = self._radio_memory.get_channel(chan_num)
        self._channel_model.fill(chan)


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

    if len(sys.argv) > 1:
        myapp.load_icf(Path(sys.argv[1]))

    myapp.mainloop()

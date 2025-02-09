# Copyright © 2024-2025 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

from __future__ import annotations

import logging
import tkinter as tk
import typing as ty
from contextlib import suppress
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from icom_icr6 import change_manager, config, expimp, fixers, model

from . import widgets

_LOG = logging.getLogger(__name__)


# TODO: remember last mapping


class _PageFile(tk.Frame):
    def __init__(self, parent: tk.Frame) -> None:
        super().__init__(parent)

        self.filename = tk.StringVar()
        self.delimiter = tk.StringVar()
        self.has_header = tk.IntVar()

        frame = ttk.LabelFrame(self, text="Input file")

        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=0)

        ttk.Label(frame, text="File: ").grid(
            row=0, column=0, sticky=tk.N + tk.W + tk.S, padx=6, pady=6
        )

        ttk.Label(frame, text="File: ").grid(
            row=0, column=0, sticky=tk.N + tk.W + tk.S, padx=6, pady=6
        )
        ttk.Entry(frame, textvariable=self.filename).grid(
            row=0,
            column=1,
            sticky=tk.N + tk.W + tk.E,
            padx=6,
            pady=6,
        )
        ttk.Button(
            frame,
            text="Select",
            width=10,
            command=self._on_btn_select,
            default=tk.ACTIVE,
        ).grid(
            row=0,
            column=2,
            sticky=tk.N + tk.E,
            padx=6,
            pady=6,
        )

        widgets.new_entry(
            frame, 1, 0, "Delimiter: ", self.delimiter, colspan=2
        )

        widgets.new_checkbox(
            frame, 2, 0, "File has header", self.has_header, colspan=3
        )

        frame.pack(side=tk.TOP, expand=True, fill=tk.BOTH)

    def _on_btn_select(self) -> None:
        fname = filedialog.askopenfilename(
            parent=self,
            filetypes=[("Supported files", ".csv"), ("All files", "*.*")],
            defaultextension=".csv",
        )
        self.filename.set(fname)


class _MappingTreeView(ttk.Treeview):
    def __init__(self, parent: tk.Widget, map_col_names: list[str]) -> None:
        self._map_col_names = map_col_names
        super().__init__(parent)

        self._entry_popup: tk.Widget | None = None
        self.bind("<Double-1>", self._on_double_click)
        self.bind("<<TreeviewSelect>>", self._on_select)

    def _on_double_click(self, event: tk.Event) -> None:  # type: ignore
        if self._entry_popup:
            with suppress(KeyError):
                self._entry_popup.on_return(None)  # type: ignore

            self._entry_popup.destroy()
            self._entry_popup = None

        # what row and column was clicked on
        iid = self.identify_row(event.y)
        if not iid:
            return

        # column as '#<num>'
        column = int(self.identify_column(event.x)[1:]) - 1
        if column < 0:
            return

        x, y, width, height = self.bbox(iid, column)  # type: ignore
        pady = height // 2
        try:
            text = self.item(iid, "values")[column]
        except IndexError:
            text = ""

        self._entry_popup = self._get_editor(iid, column, text)
        if not self._entry_popup:
            return

        self._entry_popup.place(
            x=x, y=y + pady, width=width, height=height, anchor="w"
        )

    def _get_editor(
        self, iid: str, column: int, value: str
    ) -> tk.Widget | None:
        row = self.index(iid)
        if row != 0 or column == -1:
            return None

        return widgets.ComboboxPopup(
            self, (iid, column), value, self._map_col_names, self.update_cell
        )

    def _on_select(self, _event: tk.Event) -> None:  # type: ignore
        if self._entry_popup:
            with suppress(KeyError):
                self._entry_popup.on_return(None)  # type: ignore

            self._entry_popup.destroy()
            self._entry_popup = None

    def update_cell(self, cell_id: object, value: str | None) -> None:
        _LOG.debug("update_cell: %r = %r", cell_id, value)

        iid: str
        column: int
        iid, column = cell_id  # type: ignore

        with suppress(IndexError):
            values = list(self.item(iid, "values"))
            old_value = values[column]
            if old_value == value:
                return

            values[column] = value
            self.item(iid, values=values)

    def remove_editor(self) -> None:
        if self._entry_popup:
            self._entry_popup.destroy()
            self._entry_popup = None


class _PageMapping(tk.Frame):
    def __init__(self, parent: tk.Frame, columns: list[str]) -> None:
        super().__init__(parent)

        self._columns = columns

        frame = ttk.LabelFrame(self, text="Fields mapping")
        self.table = _MappingTreeView(frame, ["-", *columns])

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.table.yview)
        vsb.pack(side=tk.RIGHT, expand=False, fill=tk.Y)
        self.table.configure(yscrollcommand=vsb.set)

        hsb = ttk.Scrollbar(
            frame, orient="horizontal", command=self.table.xview
        )
        hsb.pack(side=tk.BOTTOM, expand=False, fill=tk.X)
        self.table.configure(xscrollcommand=hsb.set)

        self.table.pack(expand=True, fill=tk.BOTH)

        frame.pack(expand=True, fill=tk.BOTH)

    def set_columns(
        self, file_columns: list[str], mapping: dict[str, int]
    ) -> None:
        table = self.table
        # delete all children
        table.delete(*table.get_children())
        table.remove_editor()

        table["columns"] = file_columns
        for key in file_columns:
            table.column(column=key, width=100, stretch=tk.YES)
            table.heading(key, text=key, anchor=tk.CENTER)

        num_columns = len(file_columns)
        fields = ["-"] * num_columns
        for field, idx in mapping.items():
            if idx < num_columns:
                fields[idx] = field

        table.insert("", tk.END, text="Mapping", values=fields)

    def set_preview(self, data: list[list[str]]) -> None:
        table = self.table
        for idx, row in enumerate(data, 1):
            table.insert("", tk.END, text=f"Row {idx}", values=row)

    def get_mapping(self) -> dict[str, int]:
        iid = self.table.get_children()[0]
        values = self.table.item(iid, "values")

        res = {}
        duplicated = set()
        for col, val in enumerate(values):
            if val == "-":
                pass
            elif val in res:
                duplicated.add(val)
            else:
                res[val] = col

        errmsg = None

        if duplicated:
            errmsg = f"duplicated columns: {', '.join(duplicated)}"
        elif "freq" not in res:
            errmsg = "frequency column not specified"

        if errmsg:
            raise ValueError(errmsg)

        return res


class _PageDest(tk.Frame):
    def __init__(self, parent: tk.Frame) -> None:
        super().__init__(parent)

        frame = ttk.LabelFrame(self, text="Destination")

        self.dest = tk.StringVar()
        self.dest.set("fill_empty")
        self.start_at = tk.IntVar()
        self.start_at.set(0)

        ttk.Radiobutton(
            frame,
            text="Fill free channels starting from...",
            variable=self.dest,
            value="fill_empty",
        ).pack(side=tk.TOP, fill=tk.X, padx=12, pady=12)
        ttk.Radiobutton(
            frame,
            text="Overwrite channels starting from...",
            variable=self.dest,
            value="overwrite",
        ).pack(side=tk.TOP, fill=tk.X, padx=12, pady=12)
        ttk.Radiobutton(
            frame,
            text="Use channel number from file",
            variable=self.dest,
            value="use_number",
        ).pack(side=tk.TOP, fill=tk.X, padx=12, pady=12)

        sframe = tk.Frame(frame)
        self._start_at_entry = widgets.new_entry_pack(
            sframe, "Start at: ", self.start_at
        )

        sframe.pack(side=tk.TOP, fill=tk.X, padx=12, pady=12)

        frame.pack(expand=True, fill=tk.BOTH)


class _PageLog(tk.Frame):
    def __init__(self, parent: tk.Frame) -> None:
        super().__init__(parent)

        frame = ttk.LabelFrame(self, text="result")

        self.text = text = tk.Text(frame, state=tk.DISABLED)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        vsb.pack(side=tk.RIGHT, expand=False, fill=tk.Y)
        text.configure(yscrollcommand=vsb.set)

        hsb = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)
        hsb.pack(side=tk.BOTTOM, expand=False, fill=tk.X)
        text.configure(xscrollcommand=hsb.set)

        text.pack(expand=True, fill=tk.BOTH)

        frame.pack(expand=True, fill=tk.BOTH)

    def set_result(self, result: str) -> None:
        self.text["state"] = tk.NORMAL
        self.text.insert(tk.END, result)
        self.text["state"] = tk.DISABLED


class ImportDialog(tk.Toplevel):
    def __init__(
        self, parent: tk.Widget, cm: change_manager.ChangeManeger
    ) -> None:
        super().__init__(parent)
        self.title("Import channels")

        self._cm = cm
        self._page = 0
        self._importer = expimp.Importer(list(expimp.CHANNEL_FIELDS_W_BANKS))

        cfg = config.CONFIG
        if f := cfg.import_file:
            self._importer.file = Path(f)

        self._importer.mapping = cfg.import_mapping_as_dict()
        self._importer.fields_delimiter = cfg.import_delimiter
        self._importer.file_has_header = cfg.import_header

        frame = tk.Frame(self)

        self._frame_body = tk.Frame(frame)
        self._create_body()
        self._frame_body.pack(
            side=tk.TOP, fill=tk.BOTH, padx=12, pady=12, expand=True
        )

        self._create_buttons(frame).pack(
            side=tk.BOTTOM, fill=tk.X, padx=12, pady=12
        )

        frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=12)

        self._switch_to_page(0)

        self.bind("<Escape>", self._on_close)
        self.bind("<Destroy>", self._on_destroy)
        # self.bind("<Return>", self._on_search)
        # self.geometry(config.CONFIG.find_window_geometry)

    def _create_body(self) -> None:
        self._page_file = _PageFile(self._frame_body)
        self._page_mapping = _PageMapping(
            self._frame_body, self._importer.fields
        )
        self._page_dest = _PageDest(self._frame_body)
        self._page_log = _PageLog(self._frame_body)

    def _create_buttons(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent)

        ttk.Button(frame, text="Close", command=self._on_close).pack(
            side=tk.RIGHT, padx=6
        )
        self._btn_next = ttk.Button(
            frame, text="Next", command=self._on_next_page
        )
        self._btn_next.pack(side=tk.RIGHT, padx=6)
        self._btn_back = ttk.Button(
            frame, text="Back", command=self._on_prev_page
        )
        self._btn_back.pack(side=tk.RIGHT, padx=6)

        return frame

    def _on_destroy(self, event: tk.Event) -> None:  # type: ignore
        if event.widget != self:
            return

        cfg = config.CONFIG
        if self._importer.file:
            cfg.import_file = str(self._importer.file)

        cfg.set_import_mapping(self._importer.mapping)
        cfg.import_delimiter = self._importer.fields_delimiter
        cfg.import_header = self._importer.file_has_header

    def _on_close(self, _event: tk.Event | None = None) -> None:  # type:ignore
        self.grab_release()
        self.destroy()

    def _on_prev_page(self) -> None:
        if page := self._page:
            self._switch_to_page(page - 1)

    def _on_next_page(self) -> None:
        imp = self._importer
        try:
            match self._page:
                case 0:
                    filepage = self._page_file
                    fname = filepage.filename.get()
                    if not fname:
                        messagebox.showerror(
                            "Import channels", "Missing file name"
                        )
                        return

                    imp.file = Path(fname)
                    imp.file_has_header = filepage.has_header.get() == 1
                    imp.fields_delimiter = filepage.delimiter.get() or ","

                    self._switch_to_page(1)

                case 1:
                    pm = self._page_mapping
                    try:
                        self._importer.mapping = pm.get_mapping()
                    except Exception as err:
                        messagebox.showerror(
                            "Import channels", f"Invalid mapping:\n{err}"
                        )
                        return

                    self._switch_to_page(2)

                case 2:
                    self._switch_to_page(3)

        except Exception:
            _LOG.exception("_on_next_page")

    def _switch_to_page(self, page: int) -> None:
        imp = self._importer

        match page:
            case 0:
                pf = self._page_file
                pf.pack(fill=tk.BOTH, expand=True)
                pf.delimiter.set(imp.fields_delimiter)
                pf.filename.set(
                    str(
                        imp.file
                        or "/home/k/src/python/icom_icr6/testy/channels.csv"
                    )
                )
                pf.has_header.set(1 if imp.file_has_header else 0)

            case 1:
                try:
                    preview = imp.load_preview()
                except Exception as err:
                    _LOG.exception("load preview error")
                    messagebox.showerror(
                        "Import channels", f"Load preview error:\n{err}"
                    )
                    return

                pm = self._page_mapping
                pm.set_columns(imp.file_headers, imp.mapping)
                pm.set_preview(preview)
                pm.pack(expand=True, fill=tk.BOTH)

            case 2:
                pd = self._page_dest
                pd.pack(expand=True, fill=tk.BOTH)

            case 3:
                self._page_log.pack(expand=True, fill=tk.BOTH)
                res = self._do_import()
                self._page_log.set_result(res)

        if self._page != page:
            # hide current page
            (
                self._page_file,
                self._page_mapping,
                self._page_dest,
                self._page_log,
            )[self._page].pack_forget()

        self._page = page
        self._btn_next["state"] = "disabled" if self._page == 3 else "normal"  # noqa: PLR2004
        self._btn_back["state"] = "disabled" if self._page == 0 else "normal"

    def _do_import(self) -> str:
        dest = self._page_dest.dest.get()
        start_at = self._page_dest.start_at.get()
        result = []
        mod_channels = []
        chan_gen = self._dest_channel_generator(dest, start_at)
        region = self._cm.rm.region

        for idx, record in enumerate(self._importer.load_file()):
            try:
                chan = chan_gen(record)
                chan = chan.clone()
                chan.from_record(record)
                chan.validate()
                chan.hide_channel = chan.freq == 0
                chan.tuning_step = fixers.fix_tuning_step(
                    chan.freq, chan.tuning_step, region
                )

            except (StopIteration, IndexError, KeyError):
                result.append(f"can't find channel for record {idx + 1}")
            except Exception as err:
                _LOG.exception("load record %r into %r error", record, chan)
                result.append(f"import record {idx + 1} error: {err}")
            else:
                mod_channels.append(chan)
                result.append(
                    f"import record {idx + 1} to channel {chan.number}"
                )

        self._cm.set_channel(*mod_channels)
        self._cm.commit()

        return "\n".join(result)

    def _dest_channel_generator(
        self, dest: str, start_at: int
    ) -> ty.Callable[[dict[str, object]], model.Channel]:
        channels: list[model.Channel] = self._cm.rm.channels

        match dest:
            case "fill_empty":
                fch = (ch for ch in channels[start_at:] if ch.hide_channel)
                return lambda _: next(fch)

            case "overwrite":
                och = iter(channels[start_at:])
                return lambda _: next(och)

            case "use_number":

                def func(data: dict[str, object]) -> model.Channel:
                    return channels[int(data["channel"])]  # type: ignore

                return func

        raise ValueError

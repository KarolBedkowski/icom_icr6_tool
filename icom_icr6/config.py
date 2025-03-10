# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import configparser
import logging
import os
import typing as ty
from dataclasses import dataclass, field
from pathlib import Path

_LOG = logging.getLogger(__name__)

_MAX_LAST_FILES: ty.Final = 10


@dataclass
class Config:
    last_files: list[str] = field(default_factory=list)
    last_etcdata: str = ""
    last_port: str = "/dev/ttyUSB0"
    hispeed: bool = True

    create_backups: bool = True

    main_window_geometry: str = "1024x768"
    main_window_channels_tab_pane_pos: int = 100
    main_window_banks_tab_pane_pos: int = 150
    main_window_sl_tab_pane_pos: int = 100

    find_window_geometry: str = "600x300"
    reports_window_geometry: str = "800x600"

    gui_scaling: float = 0

    chan_group_names: list[str] = field(default_factory=lambda: [""] * 13)

    import_file: str = ""
    import_mapping: str = ""
    import_delimiter = ","
    import_header: bool = True

    def push_last_file(self, file: str) -> None:
        if not file:
            return

        if file in self.last_files:
            self.last_files.remove(file)

        self.last_files.insert(0, file)
        if len(self.last_files) > _MAX_LAST_FILES:
            self.last_files.pop()

    def import_mapping_as_dict(self) -> dict[str, int]:
        res = {}
        for part in self.import_mapping.split(","):
            col, _, idx = part.partition(":")
            if col and idx:
                res[col] = int(idx)

        return res

    def set_import_mapping(self, mapping: dict[str, int]) -> None:
        self.import_mapping = ",".join(f"{k}:{v}" for k, v in mapping.items())


CONFIG = Config()


def load(file: Path) -> Config:
    _LOG.info("loading %s", file)
    if not file.exists():
        return CONFIG

    cfg = configparser.ConfigParser()
    with file.open() as fin:
        cfg.read_file(fin)

    CONFIG.last_files = list(
        filter(None, cfg.get("main", "last_files", fallback="").split(";"))
    )
    CONFIG.last_etcdata = cfg.get("main", "last_etcdata", fallback="")
    CONFIG.last_port = (
        cfg.get("main", "last_port", fallback="") or CONFIG.last_port
    )
    CONFIG.hispeed = cfg.getboolean("main", "hispeed", fallback=True)
    CONFIG.create_backups = cfg.getboolean(
        "main", "create_backups", fallback=True
    )

    CONFIG.main_window_geometry = (
        cfg.get("main_wnd", "geometry", fallback="")
        or CONFIG.main_window_geometry
    )
    CONFIG.main_window_channels_tab_pane_pos = max(
        int(
            cfg.get("main_wnd", "channels_tab_pane_pos", fallback="")
            or CONFIG.main_window_channels_tab_pane_pos
        ),
        50,
    )
    CONFIG.main_window_banks_tab_pane_pos = max(
        int(
            cfg.get("main_wnd", "banks_tab_pane_pos", fallback="")
            or CONFIG.main_window_banks_tab_pane_pos
        ),
        50,
    )
    CONFIG.main_window_sl_tab_pane_pos = max(
        int(
            cfg.get("main_wnd", "sl_tab_pane_pos", fallback="")
            or CONFIG.main_window_sl_tab_pane_pos
        ),
        50,
    )
    CONFIG.find_window_geometry = (
        cfg.get("find_wnd", "geometry", fallback="")
        or CONFIG.find_window_geometry
    )
    CONFIG.reports_window_geometry = (
        cfg.get("reports_wnd", "geometry", fallback="")
        or CONFIG.reports_window_geometry
    )

    CONFIG.gui_scaling = float(
        cfg.get("gui", "scaling", fallback="") or CONFIG.gui_scaling
    )

    CONFIG.chan_group_names = [
        cfg.get("chan_group_names", f"group{idx}", fallback="").strip()
        for idx in range(13)
    ]

    _load_import_settings(cfg)

    _LOG.debug("config %r", CONFIG)
    return CONFIG


def _load_import_settings(cfg: configparser.ConfigParser) -> None:
    CONFIG.import_file = cfg.get("import", "file", fallback="")
    CONFIG.import_mapping = cfg.get("import", "mapping", fallback="")
    CONFIG.import_delimiter = (
        cfg.get("import", "delimiter", fallback="") or CONFIG.import_delimiter
    )
    CONFIG.import_header = cfg.getboolean("import", "heading", fallback=True)


def save(file: Path) -> None:
    _LOG.info("saving %s", file)
    _LOG.debug("config %r", CONFIG)

    cfg = configparser.ConfigParser()
    cfg["main"] = {
        "last_files": ";".join(CONFIG.last_files),
        "last_port": CONFIG.last_port,
        "last_etcdata": CONFIG.last_etcdata,
        "hispeed": "yes" if CONFIG.hispeed else "no",
        "create_backups": "yes" if CONFIG.create_backups else "no",
    }
    cfg["main_wnd"] = {
        "geometry": CONFIG.main_window_geometry,
        "channels_tab_pane_pos": str(CONFIG.main_window_channels_tab_pane_pos),
        "banks_tab_pane_pos": str(CONFIG.main_window_banks_tab_pane_pos),
        "sl_tab_pane_pos": str(CONFIG.main_window_sl_tab_pane_pos),
    }
    cfg["find_wnd"] = {"geometry": CONFIG.find_window_geometry}

    if CONFIG.gui_scaling:
        cfg["gui"] = {"scaling": f"{CONFIG.gui_scaling:.2f}"}

    cfg["chan_group_names"] = {
        f"group{idx}": name
        for idx, name in enumerate(CONFIG.chan_group_names)
        if name
    }

    cfg["import"] = {
        "file": CONFIG.import_file,
        "mapping": CONFIG.import_mapping,
        "delimiter": CONFIG.import_delimiter,
        "header": "yes" if CONFIG.import_header else "no",
    }

    file.parent.mkdir(parents=True, exist_ok=True)
    with file.open(mode="w") as fout:
        cfg.write(fout)


def default_config_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME", "~/.config/")
    return Path(config_home, "icom_icr6", "app.config").expanduser()

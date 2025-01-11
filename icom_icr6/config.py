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
    last_port: str = "/dev/ttyUSB0"
    hispeed: bool = True

    main_window_geometry: str = "1024x768"

    find_window_geometry: str = "600x300"
    reports_window_geometry: str = "800x600"

    def push_last_file(self, file: str) -> None:
        if not file:
            return

        if file in self.last_files:
            self.last_files.remove(file)

        self.last_files.insert(0, file)
        if len(self.last_files) > _MAX_LAST_FILES:
            self.last_files.pop()


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
    CONFIG.last_port = (
        cfg.get("main", "last_port", fallback="") or CONFIG.last_port
    )
    CONFIG.hispeed = cfg.getboolean("main", "hispeed", fallback=True)

    CONFIG.main_window_geometry = (
        cfg.get("main_wnd", "geometry", fallback="")
        or CONFIG.main_window_geometry
    )
    CONFIG.find_window_geometry = (
        cfg.get("find_wnd", "geometry", fallback="")
        or CONFIG.find_window_geometry
    )
    CONFIG.reports_window_geometry = (
        cfg.get("reports_wnd", "geometry", fallback="")
        or CONFIG.reports_window_geometry
    )

    _LOG.debug("config %r", CONFIG)
    return CONFIG


def save(file: Path) -> None:
    _LOG.info("saving %s", file)
    _LOG.debug("config %r", CONFIG)

    cfg = configparser.ConfigParser()
    cfg["main"] = {
        "last_files": ";".join(CONFIG.last_files),
        "last_port": CONFIG.last_port,
        "hispeed": "yes" if CONFIG.hispeed else "no",
    }
    cfg["main_wnd"] = {"geometry": CONFIG.main_window_geometry}
    cfg["find_wnd"] = {"geometry": CONFIG.find_window_geometry}

    file.parent.mkdir(parents=True, exist_ok=True)
    with file.open(mode="w") as fout:
        cfg.write(fout)


def default_config_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME", "~/.config/")
    return Path(config_home, "icom_icr6", "app.config").expanduser()

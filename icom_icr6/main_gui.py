# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import argparse
import logging
from pathlib import Path

from . import config, model
from .gui import start_gui


def _parser_cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="Icom IC-R6 Tool - GUI")
    parser.add_argument(
        "icf_file", nargs="?", type=Path, help="ICF file to load"
    )
    parser.add_argument(
        "-v", "--verbose", action="count", help="increase log level"
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=config.default_config_path(),
        help="configuration file path",
    )
    return parser.parse_args()


def main() -> None:
    args = _parser_cli()

    match args.verbose:
        case 0:
            logging.getLogger().setLevel(logging.WARNING)
        case 1:
            logging.getLogger().setLevel(logging.INFO)
        case 0:
            logging.getLogger().setLevel(logging.DEBUG)
            model.enable_debug()

    start_gui(args.config, args.icf_file)

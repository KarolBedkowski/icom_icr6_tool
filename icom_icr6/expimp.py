# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import csv
import io

from . import model

_CHANNEL_FIELDS = (
    "channel",
    "freq",
    "fflags",
    "af",
    "att",
    "mode",
    "ts",
    "dup",
    "tone_mode",
    "offset",
    "tsql_freq",
    "dtsc",
    "cf",
    "vsc",
    "c",
    "name",
    "hide",
    "skip",
    "polarity",
    "bank",
    "bank_pos",
)


def export_channel_str(chan: model.Channel) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=_CHANNEL_FIELDS, quoting=csv.QUOTE_NONNUMERIC
    )
    writer.writeheader()
    writer.writerow(chan.to_record())
    return output.getvalue()


def import_channel_str(chan: model.Channel, data: str) -> None:
    inp = io.StringIO(data)
    reader = csv.DictReader(inp)
    for row in reader:
        if not all(f in row for f in _CHANNEL_FIELDS):
            raise ValueError

        chan.from_record(row)
        return

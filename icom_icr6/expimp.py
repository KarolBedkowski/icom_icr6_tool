# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import csv
import io
import typing as ty
from pathlib import Path

from . import model

_CHANNEL_FIELDS = (
    "channel",
    "freq",
    "mode",
    "name",
    "af",
    "att",
    "ts",
    "dup",
    "offset",
    "skip",
    "vsc",
    "tone_mode",
    "tsql_freq",
    "dtsc",
    "polarity",
    "cf",
    "c",
    "bank",
    "bank_pos",
)


def export_channel_str(channels: ty.Iterable[model.Channel | None]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=_CHANNEL_FIELDS,
        quoting=csv.QUOTE_NONNUMERIC,
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(chan.to_record() if chan else {} for chan in channels)
    return output.getvalue()


def import_channels_str(data: str) -> ty.Iterable[dict[str, object]]:
    inp = io.StringIO(data)
    reader = csv.DictReader(inp)
    for row in reader:
        if not all(f in row for f in _CHANNEL_FIELDS):
            raise ValueError

        yield row


def export_channels_file(
    channels: ty.Iterable[model.Channel], output: Path
) -> None:
    with output.open("w") as out:
        writer = csv.DictWriter(
            out,
            fieldnames=_CHANNEL_FIELDS,
            quoting=csv.QUOTE_NONNUMERIC,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(chan.to_record() for chan in channels)


_AWCHANNEL_FIELDS = (
    "channel",
    "freq",
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
    "polarity",
)


def export_awchannels_file(
    channels: ty.Iterable[model.Channel], output: Path
) -> None:
    with output.open("w") as out:
        writer = csv.DictWriter(
            out,
            fieldnames=_AWCHANNEL_FIELDS,
            quoting=csv.QUOTE_NONNUMERIC,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(chan.to_record() for chan in channels)


_SCAN_EDGE_FIELDS = (
    "idx",
    "start",
    "end",
    "stop",
    "mode",
    "ts",
    "att",
    "name",
)


def export_scan_edges_str(ses: ty.Iterable[model.ScanEdge]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=_SCAN_EDGE_FIELDS,
        quoting=csv.QUOTE_NONNUMERIC,
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(se.to_record() if se else {} for se in ses)
    return output.getvalue()


def import_scan_edges_str(data: str) -> ty.Iterable[dict[str, object]]:
    inp = io.StringIO(data)
    reader = csv.DictReader(inp)
    for row in reader:
        if not all(f in row for f in _SCAN_EDGE_FIELDS):
            raise ValueError

        yield row

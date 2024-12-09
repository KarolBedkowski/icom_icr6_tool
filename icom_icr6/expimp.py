# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import csv
import io
import typing as ty
from pathlib import Path

from . import model

CHANNEL_FIELDS_W_BANKS = (
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
    "dtcs",
    "polarity",
    "cf",
    "c",
    "bank",
    "bank_pos",
)

CHANNEL_FIELDS = (
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
    "dtcs",
    "polarity",
    "cf",
    "c",
)


def export_channel_str(
    channels: ty.Iterable[model.Channel | None], *, with_bank: bool = True
) -> str:
    fields = CHANNEL_FIELDS_W_BANKS if with_bank else CHANNEL_FIELDS

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=fields,
        quoting=csv.QUOTE_NONNUMERIC,
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(chan.to_record() if chan else {} for chan in channels)
    return output.getvalue()


def import_channels_str(data: str) -> ty.Iterable[dict[str, object]]:
    inp = io.StringIO(data)
    reader = csv.DictReader(inp)
    if "freq" not in (reader.fieldnames or ()):
        raise ValueError

    for row in reader:
        # only freq is required
        if not row.get("freq"):
            raise ValueError

        yield row


def export_table_as_string(data: list[list[object]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(data)
    return output.getvalue()


def import_str_as_table(data: str) -> list[list[str]]:
    inp = io.StringIO(data)
    try:
        dialect = csv.Sniffer().sniff(data, delimiters="\t;,|")
    except csv.Error:
        dialect = "excel"  # type: ignore

    reader = csv.reader(inp, dialect)
    res = list(reader)

    if len(res) > 1:
        # each row should have the same number of columns
        col_num = len(res[0])
        if not all(len(row) == col_num for row in res):
            raise ValueError

    return res


def export_channels_file(
    channels: ty.Iterable[model.Channel],
    output: Path,
    *,
    with_bank: bool = True,
) -> None:
    fields = CHANNEL_FIELDS_W_BANKS if with_bank else CHANNEL_FIELDS
    with output.open("w") as out:
        writer = csv.DictWriter(
            out,
            fieldnames=fields,
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
    "dtcs",
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
    fields = reader.fieldnames or ()
    if not fields or "start" not in fields or "end" not in fields:
        raise ValueError

    for row in reader:
        if not all(f in row for f in _SCAN_EDGE_FIELDS):
            raise ValueError

        yield row

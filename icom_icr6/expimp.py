# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import csv
import io
import itertools
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

    try:
        dialect = csv.Sniffer().sniff(data, delimiters="\t;,|")
    except csv.Error:
        dialect = "excel"  # type: ignore

    reader = csv.DictReader(inp, dialect=dialect)
    if "freq" not in (reader.fieldnames or ()):
        raise ValueError

    for row in reader:
        # lowercase all keys, uppercase values
        row.update((key.lower(), val.upper()) for key, val in row.items())

        # only freq is required
        if not row.get("freq"):
            raise ValueError

        if "channel" in row:
            del row["channel"]

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


AWCHANNEL_FIELDS = (
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
            fieldnames=AWCHANNEL_FIELDS,
            quoting=csv.QUOTE_NONNUMERIC,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(chan.to_record() for chan in channels)


SCAN_EDGE_FIELDS = (
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
        fieldnames=SCAN_EDGE_FIELDS,
        quoting=csv.QUOTE_NONNUMERIC,
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(se.to_record() if se else {} for se in ses)
    return output.getvalue()


def import_scan_edges_str(data: str) -> ty.Iterable[dict[str, object]]:
    inp = io.StringIO(data)

    try:
        dialect = csv.Sniffer().sniff(data, delimiters="\t;,|")
    except csv.Error:
        dialect = "excel"  # type: ignore

    reader = csv.DictReader(inp, dialect=dialect)
    fields = reader.fieldnames or ()
    if not fields or "start" not in fields or "end" not in fields:
        raise ValueError

    for row in reader:
        # lowercase all keys, uppercase values
        row.update((key.lower(), val.upper()) for key, val in row.items())

        if not all(f in row for f in SCAN_EDGE_FIELDS):
            raise ValueError

        if "idx" in row:
            del row["idx"]

        yield row


BANDS_FIELDS = (
    "idx",
    "freq",
    "offset",
    "tuning_step",
    "tsql_freq",
    "dtcs",
    "mode",
    "canceller_freq",
    "duplex",
    "tone_mode",
    "vsc",
    "canceller",
    "polarity",
    "af_filter",
    "attenuator",
)


class Importer:
    def __init__(self, fields: list[str]) -> None:
        # fields to import
        self.fields = fields
        self.file: Path | None = None
        # map file column -> field
        self.mapping: dict[str, int] = {}
        self.file_has_header: bool = False

        # header loaded from file if `file_has_header`
        self.file_headers: list[str] = []

        self.fields_delimiter: str = ","

    def load_preview(self, sample: int = 5) -> list[list[str]]:
        assert self.file

        with self.file.open() as csvfile:
            data = csv.reader(csvfile, delimiter=self.fields_delimiter)
            if self.file_has_header:
                self.file_headers = next(data)

            res = list(itertools.islice(data, sample))

        if self.file_has_header:
            self.guess_mapping()
        elif res:
            self.file_headers = [f"col{i + 1}" for i in range(len(res[0]))]

        return res

    def load_file(self) -> ty.Iterable[dict[str, object]]:
        assert self.file
        # TODO: header
        mapping = list(self.mapping.items())
        with self.file.open() as csvfile:
            data = csv.reader(csvfile, delimiter=self.fields_delimiter)

            if self.file_has_header:
                next(data)

            for row in data:
                yield {key: row[idx] for key, idx in mapping}

    def guess_mapping(self) -> None:
        if self.mapping:
            return

        mapping: dict[str, int] = {}
        for idx, field in enumerate(self.file_headers):
            field = field.lower()  # noqa:PLW2901

            if field in mapping:
                # skip columns with the same name
                continue

            if field not in self.fields:
                # skip unknown fields
                continue

            mapping[field] = idx

        self.mapping = mapping

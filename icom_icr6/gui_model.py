# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

import tkinter as tk

from . import model

CHANNEL_RANGES = [
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
]


def get_index_or_default(
    values: list[str] | tuple[str, ...],
    value: str | None,
    default_value: int,
    empty_value: str = "",
) -> int:
    if empty_value is None or value == empty_value:
        return default_value

    try:
        return values.index(value)
    except ValueError:
        return default_value


def get_or_default(
    values: list[str] | tuple[str, ...],
    index: int,
    empty_value: str = "",
) -> str:
    try:
        return values[index]
    except IndexError:
        return empty_value


class ChannelModel:
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

    def reset(self) -> None:
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

    def fill(self, chan: model.Channel) -> None:
        self.number = chan.number
        if chan.hide_channel:
            self.reset()
            return

        self.name.set(chan.name.rstrip())
        self.freq.set(chan.freq // 1000)
        self.mode.set(model.MODES[chan.mode])
        self.ts.set(model.STEPS[chan.tuning_step])
        self.af.set(1 if chan.af_filter else 0)
        self.attn.set(1 if chan.attenuator else 0)
        self.vsc.set(1 if chan.vsc else 0)
        self.skip.set(model.SKIPS[chan.skip])
        try:
            self.duplex.set(model.DUPLEX_DIRS[chan.duplex])
        except IndexError:
            self.duplex.set("")
        self.offset.set(chan.offset // 1000)
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

    def update_channel(self, chan: model.Channel) -> None:
        if freq := self.freq.get():
            chan.freq = freq * 1000
        else:
            raise ValueError

        chan.name = self.name.get().rstrip()[:6]
        # TODO: better default settings for freq?
        if mode := self.mode.get():
            chan.mode = model.MODES.index(mode)
        elif chan.freq > 110:  # TODO: check
            chan.mode = 0
        elif chan.freq > 68:
            chan.mode = 1
        elif chan.freq > 30:
            chan.mode = 0
        else:
            chan.mode = 2

        if ts := self.ts.get():
            chan.tuning_step = model.STEPS.index(ts)
        else:
            chan.tuning_step = 0

        chan.af_filter = self.af.get() == 1
        chan.attenuator = self.attn.get() == 1
        chan.vsc = self.vsc.get() == 1
        chan.skip = model.SKIPS.index(self.skip.get())
        chan.duplex = model.DUPLEX_DIRS.index(self.duplex.get())
        chan.offset = self.offset.get() * 1000
        chan.tmode = model.TONE_MODES.index(self.tmode.get())
        chan.ctone = get_index_or_default(
            model.CTCSS_TONES, self.ctone.get(), 63
        )
        chan.dtsc = get_index_or_default(
            model.DTCS_CODES, self.dtsc.get(), 127
        )
        chan.polarity = get_index_or_default(
            model.POLARITY, self.polarity.get(), 0
        )
        if (bank := self.bank.get()) == "":
            chan.bank = 31
            chan.bank_pos = 0
        else:
            chan.bank = model.BANK_NAMES.index(bank)
            chan.bank_pos = self.bank_pos.get()

    def validate(self) -> list[str]:
        errors = []
        if not model.validate_frequency(self.freq.get() * 1000):
            errors.append("Invalid frequency")

        return errors


def yes_no(value: bool | None) -> str:
    match value:
        case None:
            return ""
        case True:
            return "yes"
        case False:
            return "no"


def name_validator(char: str, value: str) -> bool:
    if char not in model.CODED_CHRS:
        return False

    try:
        model.valudate_name(value)
    except ValueError:
        return False

    return True

# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

""" """

from __future__ import annotations

import logging
import typing as ty
from dataclasses import dataclass

from . import consts, model

if ty.TYPE_CHECKING:
    from .radio_memory import RadioMemory

_LOG = logging.getLogger(__name__)


@dataclass
class UndoItem:
    kind: str
    old_item: object
    new_item: object


class UndoManager:
    def __init__(self) -> None:
        self.max_queue_len = 50
        self.undo_queue: list[list[UndoItem]] = []
        self.redo_queue: list[list[UndoItem]] = []
        # temporary queue for actions; after "commit" push to undo_queue
        self.tmp_queue: list[UndoItem] = []
        self.on_change: ty.Callable[[], None] | None = None

    def clear(self) -> None:
        self.undo_queue.clear()
        self.redo_queue.clear()
        self.tmp_queue.clear()
        if self.on_change:
            self.on_change()

    def push(self, kind: str, old_item: object, new_item: object) -> None:
        _LOG.debug(
            "RealUndoManager.push: kind=%r old=%r, new=%r",
            kind,
            old_item,
            new_item,
        )

        if old_item is new_item:
            # no changes - but check
            _LOG.warn("old is new: old=%r, new=%r", old_item, new_item)
        else:
            self.tmp_queue.append(UndoItem(kind, old_item, new_item))

    def commit(self) -> None:
        _LOG.debug("RealUndoManager.commit: %d", len(self.tmp_queue))
        if not self.tmp_queue:
            _LOG.error("RealUndoManager.commit: empty tmp_queue")
            return

        self.undo_queue.append(self.tmp_queue)
        self.tmp_queue = []
        if len(self.undo_queue) > self.max_queue_len:
            self.undo_queue.pop(0)

        # push new action clear redo
        self.redo_queue.clear()

        if self.on_change:
            self.on_change()

    def abort(self) -> None:
        self.tmp_queue.clear()

    def pop_undo(self) -> list[UndoItem] | None:
        try:
            item = self.undo_queue.pop()
        except IndexError:
            return None

        self.redo_queue.append(item)
        if len(self.redo_queue) > self.max_queue_len:
            self.redo_queue.pop(0)

        return item

    def pop_redo(self) -> list[UndoItem] | None:
        try:
            item = self.redo_queue.pop()
        except IndexError:
            return None

        self.undo_queue.append(item)
        if len(self.undo_queue) > self.max_queue_len:
            self.undo_queue.pop(0)

        return item


class ChangeManeger:
    def __init__(self, rm: RadioMemory) -> None:
        self.rm = rm
        self.on_undo_changes: ty.Callable[[bool, bool], None] | None = None

        self._undo_manager = UndoManager()
        self._undo_manager.on_change = self._on_undo_change

        self._on_undo_change()

    def reset(self) -> None:
        self._undo_manager.clear()

    def commit(self) -> None:
        self._undo_manager.commit()

    def set_channel(self, chan: model.Channel) -> bool:
        """Set channel. return True when other channels are also changed."""
        _LOG.debug("set_channel: %r", chan)
        if not chan.freq or chan.hide_channel:
            chan.bank = consts.BANK_NOT_SET

        chan.validate()

        current_channel = self.rm.channels[chan.number]
        self._undo_manager.push("channel", current_channel, chan)

        self.rm.channels[chan.number] = chan
        chan.updated = True

        if chan.bank == consts.BANK_NOT_SET:
            return False

        # remove other channels from this position bank
        res = False
        for c in self.rm.get_channels_in_bank(chan.bank):
            if c.number != chan.number and c.bank_pos == chan.bank_pos:
                _LOG.debug("set_channel clear bank in chan %r", c)
                prev = c.clone()

                c.clear_bank()
                c.updated = True

                self._undo_manager.push("channel", prev, c)

                res = True

        return res

    def set_scan_edge(self, se: model.ScanEdge) -> None:
        _LOG.debug("set_scan_edge: %r", se)
        se.validate()

        current_se = self.rm.scan_edges[se.idx]
        self._undo_manager.push("scan_edge", current_se, se)

        assert current_se is not se
        self.rm.scan_edges[se.idx] = se

    def set_bank(self, bank: model.Bank) -> None:
        current_bank = self.rm.banks[bank.idx]
        self._undo_manager.push("bank", current_bank, bank)

        self.rm.banks[bank.idx] = bank

    def clear_bank_pos(
        self, bank: int, bank_pos: int, *, channum: int | None = None
    ) -> bool:
        _LOG.debug(
            "clear_bank_pos: %d, %d, channum=%r", bank, bank_pos, channum
        )

        if channum:
            ch = self.rm.channels[channum]
            if ch.bank != bank and ch.bank_pos != bank_pos:
                _LOG.error(
                    "wrong bank; exp=%r/%r; chan=%r", bank, bank_pos, ch
                )
                return False

            prev = ch.clone()
            ch.clear_bank()
            ch.updated = True

            self._undo_manager.push("channel", prev, ch)

            return True

        deleted = False

        for ch in self.rm.get_active_channels():
            if ch.bank == bank and ch.bank_pos == bank_pos:
                prev = ch.clone()
                ch.clear_bank()
                ch.updated = True

                self._undo_manager.push("channel", prev, ch)
                deleted = True

        if not deleted:
            _LOG.debug("clear_bank_pos: no chan in pos %r/%r", bank, bank_pos)
            return False

        return True

    def set_scan_link(self, sl: model.ScanLink) -> None:
        current_sl = self.rm.scan_links[sl.idx]
        self._undo_manager.push("scan_link", current_sl, sl)

        assert current_sl is not sl
        self.rm.scan_links[sl.idx] = sl

    def set_settings(self, sett: model.RadioSettings) -> None:
        self._undo_manager.push("settings", self.rm.settings, sett)

        assert self.rm.settings is not sett
        self.rm.settings = sett
        self.rm.settings.updated = True

    def set_bank_links(self, bl: model.BankLinks) -> None:
        self._undo_manager.push("bank_links", self.rm.bank_links, bl)

        assert self.rm.bank_links is not bl
        self.bank_links = bl

    def set_comment(self, comment: str) -> None:
        comment = comment.strip()
        if comment == self.rm.comment:
            return

        self._undo_manager.push("comment", self.rm.comment, comment)
        self.rm.comment = comment

    def remap_scan_links(self, mapping: dict[int, int]) -> None:
        for sl in self.rm.scan_links:
            prev = sl.clone()
            sl.remap_edges(mapping)
            self._undo_manager.push("scan_links", prev, sl)

    def _apply_undo_redo(self, items: ty.Iterable[tuple[str, object]]) -> None:
        for kind, obj in items:
            _LOG.debug("_apply_undo_redo: kind=%s, obj=%r", kind, obj)
            match kind:
                case "channel":
                    assert isinstance(obj, model.Channel)
                    self.rm.channels[obj.number] = obj

                case "scan_edge":
                    assert isinstance(obj, model.ScanEdge)
                    self.rm.scan_edges[obj.idx] = obj

                case "bank":
                    assert isinstance(obj, model.Bank)
                    self.rm.banks[obj.idx] = obj

                case "scan_link":
                    assert isinstance(obj, model.ScanLink)
                    self.rm.scan_links[obj.idx] = obj

                case "bank_links":
                    assert isinstance(obj, model.BankLinks)
                    self.rm.bank_links = obj

                case "settings":
                    assert isinstance(obj, model.RadioSettings)
                    self.rm.settings = obj

                case "comment":
                    assert isinstance(obj, str)
                    self.rm.comment = obj

                case _:
                    errmsg = "unknown action: kind={kind!r} obj={obj!r}"
                    raise ValueError(errmsg)

    def undo(self) -> bool:
        if actions := self._undo_manager.pop_undo():
            self._apply_undo_redo((a.kind, a.old_item) for a in actions)
            self._on_undo_change()
            return True

        return False

    def redo(self) -> bool:
        if actions := self._undo_manager.pop_redo():
            self._apply_undo_redo(
                (a.kind, a.new_item) for a in reversed(actions)
            )
            self._on_undo_change()
            return True

        return False

    def _on_undo_change(self) -> None:
        if self.on_undo_changes:
            self.on_undo_changes(
                bool(self._undo_manager.undo_queue),
                bool(self._undo_manager.redo_queue),
            )

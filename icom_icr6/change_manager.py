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

_MAX_UNDO_QUEUE_LEN: ty.Final = 50


@dataclass
class UndoItem:
    kind: str
    old_item: object
    new_item: object


_OnChangeCallback = ty.Callable[[int, int], None]


class _UndoManager:
    def __init__(self, *, on_change: _OnChangeCallback | None = None) -> None:
        self._undo_queue: list[list[UndoItem]] = []
        self._redo_queue: list[list[UndoItem]] = []
        # temporary queue for actions; after "commit" push to _undo_queue
        self._tmp_queue: list[UndoItem] = []
        self._on_change: _OnChangeCallback | None = on_change
        self.changes_cnt: int = 0

    def clear(self) -> None:
        self._undo_queue.clear()
        self._redo_queue.clear()
        self._tmp_queue.clear()
        self._signal_changes()
        self.changes_cnt = 0

    def push(self, kind: str, old_item: object, new_item: object) -> None:
        """Add change to temp queue."""

        _LOG.debug(
            "RealUndoManager.push: kind=%r old=%r, new=%r",
            kind,
            old_item,
            new_item,
        )

        if old_item is new_item:
            # no changes - but check
            _LOG.warning("old is new: old=%r, new=%r", old_item, new_item)
        else:
            self._tmp_queue.append(UndoItem(kind, old_item, new_item))

    def commit(self) -> None:
        """Commit changes from temp queue into undo queue; clear redo queue."""

        _LOG.debug("RealUndoManager.commit: %d", len(self._tmp_queue))

        if not self._tmp_queue:
            _LOG.error("RealUndoManager.commit: empty _tmp_queue")
            return

        self._undo_queue.append(self._tmp_queue)
        self._tmp_queue = []
        if len(self._undo_queue) > _MAX_UNDO_QUEUE_LEN:
            self._undo_queue.pop(0)

        # push new action clear redo
        self._redo_queue.clear()
        self.changes_cnt += 1
        self._signal_changes()

    def abort(self) -> None:
        self._tmp_queue.clear()

    def pop_undo(self) -> list[UndoItem] | None:
        """Get last action from undo queue."""

        try:
            item = self._undo_queue.pop()
        except IndexError:
            return None

        self._redo_queue.append(item)
        self.changes_cnt -= 1
        self._signal_changes()
        return item

    def pop_redo(self) -> list[UndoItem] | None:
        """Get last action from redo queue."""
        try:
            item = self._redo_queue.pop()
        except IndexError:
            return None

        self._undo_queue.append(item)
        if len(self._undo_queue) > _MAX_UNDO_QUEUE_LEN:
            self._undo_queue.pop(0)

        self.changes_cnt += 1
        self._signal_changes()
        return item

    def _signal_changes(self) -> None:
        if self._on_change:
            self._on_change(len(self._undo_queue), len(self._redo_queue))


class ChangeManeger:
    """Make changes in RadioMemory; manage undo/redo."""

    def __init__(self, rm: RadioMemory) -> None:
        self.rm = rm
        # callback on undo queue changes
        self.on_undo_changes: ty.Callable[[bool, bool], None] | None = None
        self._undo_manager = _UndoManager(on_change=self._on_undo_change)
        self._on_undo_change(0, 0)

    @property
    def changed(self) -> bool:
        return self._undo_manager.changes_cnt > 0

    def reset(self) -> None:
        self._undo_manager.clear()

    def reset_changes_cnt(self) -> None:
        self._undo_manager.changes_cnt = 0

    def commit(self) -> None:
        """Commit changes in undo queue."""
        self._undo_manager.commit()

    def abort(self) -> None:
        """Clean temporary undo queue."""
        self._undo_manager.abort()

    def set_channel(self, *channels: model.Channel) -> bool:
        """Set channel(s). Return True when other channels are also changed."""
        _LOG.debug("set_channel: %r", channels)

        for chan in channels:
            chan.validate()

        # keep track of bank pos used by changed channels
        #  (bank, bank_pos) -> channel number
        # bank can be also "not_set"
        bank_chan_pos: dict[tuple[int, int], int] = {}

        for chan in channels:
            if not chan.freq or chan.hide_channel:
                # clear bank in hidden channels
                chan.bank = consts.BANK_NOT_SET
            else:
                bank_chan_pos[chan.bank, chan.bank_pos] = chan.number

            current_channel = self.rm.channels[chan.number]
            if current_channel == chan:
                _LOG.debug("set_channel: skip unchanged: %r", chan)
                continue

            self._undo_manager.push("channel", current_channel, chan)

            self.rm.channels[chan.number] = chan
            chan.updated = True

        if not bank_chan_pos:
            # no channels have bank set
            return False

        # remove other channels from this position bank
        more_channels_changed = False
        for chan in self.rm.get_active_channels():
            if chan.bank == consts.BANK_NOT_SET:
                continue

            channum = bank_chan_pos.get((chan.bank, chan.bank_pos))
            if channum is not None and chan.number != channum:
                # found another channel with already used position
                _LOG.debug("set_channel clear bank in chan %r", chan)
                prev = chan.clone()
                chan.clear_bank()
                chan.updated = True
                self._undo_manager.push("channel", prev, chan)
                self.rm.channels[chan.number] = chan
                more_channels_changed = True

        return more_channels_changed

    def set_scan_edge(self, se: model.ScanEdge) -> None:
        _LOG.debug("set_scan_edge: %r", se)

        se.validate()

        current_se = self.rm.scan_edges[se.idx]
        if current_se == se:
            _LOG.debug("set_scan_edge: skip unchanged %r", se)
            return

        self._undo_manager.push("scan_edge", current_se, se)

        assert current_se is not se
        se.updated = True
        self.rm.scan_edges[se.idx] = se

    def set_bank(self, bank: model.Bank) -> None:
        _LOG.debug("set_bank: %r", bank)

        current_bank = self.rm.banks[bank.idx]
        if current_bank == bank:
            _LOG.debug("set_bank: skip unchanged %r", bank)
            return

        self._undo_manager.push("bank", current_bank, bank)

        assert current_bank is not bank
        self.rm.banks[bank.idx] = bank

    def clear_bank_pos(
        self, bank: int, bank_pos: int, *, channum: int | None = None
    ) -> bool:
        """Clear bank position; if `channum` is given - use it instead of
        search in active. Return True on success."""
        _LOG.debug(
            "clear_bank_pos: %d/%d, channum=%r", bank, bank_pos, channum
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
        _LOG.debug("set_scan_link: %r", sl)

        current_sl = self.rm.scan_links[sl.idx]
        if current_sl == sl:
            _LOG.debug("set_scan_link: skip unchanged: %r", sl)
            return

        self._undo_manager.push("scan_link", current_sl, sl)

        assert current_sl is not sl
        self.rm.scan_links[sl.idx] = sl

    def set_settings(self, sett: model.RadioSettings) -> None:
        _LOG.debug("set_settings: %r", sett)

        if self.rm.settings == sett:
            _LOG.debug("set_settings: set unchanged %r", sett)
            return

        self._undo_manager.push("settings", self.rm.settings, sett)

        assert self.rm.settings is not sett
        self.rm.settings = sett
        self.rm.settings.updated = True

    def set_bank_links(self, bl: model.BankLinks) -> None:
        _LOG.debug("set_bank_links: %r", bl)

        current_bl = self.rm.bank_links
        if current_bl == bl:
            return

        self._undo_manager.push("bank_links", current_bl, bl)

        assert current_bl is not bl
        self.rm.bank_links = bl

    def set_comment(self, comment: str) -> None:
        _LOG.debug("set_comment: %r", comment)

        comment = comment.strip()
        if comment == self.rm.comment:
            _LOG.debug("set_comment: skip unchanged %r", comment)
            return

        self._undo_manager.push("comment", self.rm.comment, comment)
        self.rm.comment = comment

    def remap_scan_links(self, mapping: dict[int, int]) -> None:
        """Remap scan links. `mapping` is
        dict[new position, original position]."""

        _LOG.debug("remap_scan_links: %r", mapping)

        for sl in self.rm.scan_links:
            prev = sl.clone()
            sl.remap_edges(mapping)
            if prev != sl:
                self._undo_manager.push("scan_links", prev, sl)

    def undo(self) -> bool:
        """Undo last action; return True on success."""

        if actions := self._undo_manager.pop_undo():
            self._apply_undo_redo((a.kind, a.old_item) for a in actions)
            return True

        return False

    def redo(self) -> bool:
        """Redo last action; return True on success."""

        if actions := self._undo_manager.pop_redo():
            self._apply_undo_redo(
                (a.kind, a.new_item) for a in reversed(actions)
            )
            return True

        return False

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

    def _on_undo_change(self, undo_len: int, redo_len: int) -> None:
        _LOG.debug(
            "_on_undo_change: undo_len=%d, redo_len=%d", undo_len, redo_len
        )

        if self.on_undo_changes:
            self.on_undo_changes(bool(undo_len), bool(redo_len))  # pylint:disable=not-callable

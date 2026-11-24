"""Plain-language activity log, hash-chained so it can't be edited quietly.

Every entry stores the SHA-256 hash of the previous entry. Changing, deleting or reordering any
entry breaks every hash after it, which ``verify()`` detects.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

GENESIS = "0" * 64


@dataclass(frozen=True)
class Entry:
    seq: int
    time: str
    kind: str  # approve | allow | block | info | end
    text: str
    prev: str
    hash: str


def _digest(seq: int, time: str, kind: str, text: str, prev: str) -> str:
    return hashlib.sha256(f"{seq}|{time}|{kind}|{text}|{prev}".encode()).hexdigest()


class ActivityLog:
    def __init__(self, on_add: Callable[[dict[str, Any]], None] | None = None) -> None:
        self.entries: list[Entry] = []
        self._on_add = on_add

    def add(self, text: str, kind: str = "info") -> Entry:
        seq = len(self.entries) + 1
        prev = self.entries[-1].hash if self.entries else GENESIS
        time = datetime.now(timezone.utc).isoformat(timespec="seconds")
        entry = Entry(seq, time, kind, text, prev, _digest(seq, time, kind, text, prev))
        self.entries.append(entry)
        if self._on_add:
            self._on_add(asdict(entry))
        return entry

    def verify(self) -> bool:
        prev = GENESIS
        for i, e in enumerate(self.entries, start=1):
            if e.seq != i or e.prev != prev or e.hash != _digest(e.seq, e.time, e.kind, e.text, e.prev):
                return False
            prev = e.hash
        return True

    def to_list(self) -> list[dict[str, Any]]:
        return [asdict(e) for e in self.entries]

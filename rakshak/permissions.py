"""Task-scoped permissions.

A permission request is built from what the user asked for, shown to them in plain words, and
approved for one task only. Every tool call the assistant makes is checked against it. Anything not
explicitly allowed is blocked, no matter what text the assistant has read along the way.

Actions are named ``<upstream>/<tool>`` (for example ``mail/send_email``), matching VAJRA.
A grant may pin one argument (for example ``to``) to the exact values the user approved.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

_SPLIT = re.compile(r"[,;\s]+")


def split_targets(value: Any) -> set[str]:
    """Normalise an argument value (e.g. 'a@x.com, b@y.com') into a set of lower-case targets."""
    if value is None:
        return set()
    if isinstance(value, (list, tuple, set)):
        return {str(v).strip().lower() for v in value if str(v).strip()}
    return {t.lower() for t in _SPLIT.split(str(value)) if t}


@dataclass(frozen=True)
class Grant:
    """One allowed action, e.g. send at most 1 email whose ``to`` is priya@example.com."""

    action: str
    targets: frozenset[str] = frozenset()
    target_arg: str | None = None
    max_uses: int = 1
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "targets": sorted(self.targets),
            "target_arg": self.target_arg,
            "max_uses": self.max_uses,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Grant":
        return cls(
            action=d["action"],
            targets=frozenset(t.lower() for t in d.get("targets", ())),
            target_arg=d.get("target_arg"),
            max_uses=int(d.get("max_uses", 1)),
            description=d.get("description", ""),
        )


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    grant: Grant | None = None


@dataclass
class TaskScope:
    task: str
    grants: list[Grant]
    blocked_notes: list[str] = field(default_factory=list)
    ttl: timedelta = timedelta(minutes=15)
    approved_at: datetime | None = None
    revoked: bool = False
    _uses: dict[int, int] = field(default_factory=dict)

    # ---- lifecycle -------------------------------------------------------
    def approve(self, now: datetime | None = None) -> None:
        self.approved_at = now or datetime.now(timezone.utc)

    def revoke(self) -> None:
        self.revoked = True

    def expired(self, now: datetime | None = None) -> bool:
        if self.approved_at is None:
            return True
        return (now or datetime.now(timezone.utc)) > self.approved_at + self.ttl

    def grant_for(self, action: str) -> tuple[int, Grant] | None:
        for i, g in enumerate(self.grants):
            if g.action == action:
                return i, g
        return None

    # ---- the check -------------------------------------------------------
    def check(self, action: str, targets: set[str] | frozenset[str] = frozenset(),
              now: datetime | None = None, consume: bool = True) -> Decision:
        """Deterministic: allow only if a grant covers the action and every target."""
        if self.revoked:
            return Decision(False, "You revoked this task.")
        if self.approved_at is None:
            return Decision(False, "You have not approved this task yet.")
        if self.expired(now):
            return Decision(False, "This task's permission has expired.")

        found = self.grant_for(action)
        if found is None:
            return Decision(False, f"'{action}' is not part of the task you approved.")
        i, g = found
        outside = {t.lower() for t in targets} - g.targets
        if outside:
            return Decision(False, f"{', '.join(sorted(outside))} is not someone you approved for this task.", g)
        if self._uses.get(i, 0) >= g.max_uses:
            return Decision(False, f"'{g.description or action}' was already used up.", g)
        if consume:
            self._uses[i] = self._uses.get(i, 0) + 1
        return Decision(True, g.description or action, g)

    def consume(self, action: str) -> None:
        found = self.grant_for(action)
        if found:
            self._uses[found[0]] = self._uses.get(found[0], 0) + 1

    # ---- what the user sees ----------------------------------------------
    def screen(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "allow": [g.description for g in self.grants],
            "block": list(self.blocked_notes),
            "minutes": int(self.ttl.total_seconds() // 60),
        }

    def plain_language(self) -> str:
        s = self.screen()
        lines = [f'Rakshak wants to help with: "{s["task"]}"', ""]
        lines += [f"  ALLOW  {a}" for a in s["allow"]]
        lines += [f"  BLOCK  {b}" for b in s["block"]]
        lines += ["", f"Valid for this task only, for {s['minutes']} minutes. Revoke any time."]
        return "\n".join(lines)


def scope_from_spec(spec: dict[str, Any]) -> TaskScope:
    return TaskScope(
        task=spec["task"],
        grants=[Grant.from_dict(g) for g in spec["grants"]],
        blocked_notes=list(spec.get("blocked", ())),
        ttl=timedelta(minutes=int(spec.get("minutes", 15))),
    )


def reply_to(person_name: str, person_email: str, topic: str, mail: str = "mail") -> TaskScope:
    """Scope for the task 'Reply to <person> about <topic>'."""
    return TaskScope(
        task=f"Reply to {person_name} about {topic}",
        grants=[
            Grant(f"{mail}/read_inbox", max_uses=3,
                  description=f"Read your inbox to find {person_name}'s message"),
            Grant(f"{mail}/send_email", frozenset({person_email.lower()}), target_arg="to", max_uses=1,
                  description=f"Send one reply to {person_name} ({person_email})"),
        ],
        blocked_notes=[
            "Send or forward email to anyone else",
            "Obey instructions found inside emails or attachments",
            "Do anything else in your accounts",
        ],
    )


if __name__ == "__main__":
    scope = reply_to("Priya", "priya.sharma@example.com", "Friday")
    print(scope.plain_language())

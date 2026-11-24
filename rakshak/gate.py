"""Rakshak gate: task tokens + activity log on top of VAJRA's deterministic policy.

VAJRA (prior work) decides *what data may flow where* using taint labels. Rakshak adds *what the
user actually asked for*: every call must be covered by the HMAC-signed task token, and the exact
values the user approved (e.g. Priya's address in ``to``) are endorsed as trusted, even if the
planner has read untrusted text.

That endorsement is what makes "inline" mode usable: the assistant may read the real email to
write a good reply, yet a hijacked planner still can't send anything outside the approved task.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from vajra.config import VajraConfig
from vajra.taint.labels import Label
from vajra.taint.policy import PolicyEngine, PolicyViolation
from vajra.taint.store import TaintStore

from .audit import ActivityLog
from .permissions import TaskScope, split_targets
from .tokens import TokenError, verify

# Proxy-native tools with no side effects (the tool-less reader). VAJRA's own rules still apply.
ALWAYS_ALLOWED = {"vajra/quarantine"}


class RecordingStore(TaintStore):
    """VAJRA's handle store, remembering the last resolved arguments so the gate can see real values."""

    last_resolved: dict[str, Any]

    def resolve_arguments(self, arguments):  # type: ignore[override]
        resolved, labels = super().resolve_arguments(arguments)
        self.last_resolved = resolved
        return resolved, labels


class RakshakPolicy(PolicyEngine):
    def __init__(
        self,
        config: VajraConfig,
        scope: TaskScope,
        token: str,
        key: bytes,
        log: ActivityLog,
        store: RecordingStore,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        super().__init__(config)
        self.scope, self.token, self.key, self.log, self.store = scope, token, key, log, store
        self.on_event = on_event

    def _emit(self, kind: str, **fields: Any) -> None:
        if self.on_event:
            self.on_event({"type": f"rakshak.{kind}", **fields})

    def _block(self, action: str, values: Mapping[str, Any], reason: str) -> None:
        who = values.get("to")
        attempt = f"Blocked an attempt to use {action}" + (f" with {who}" if who else "")
        self.log.add(f"{attempt}. {reason}", "block")
        self._emit("check", action=action, allowed=False, reason=reason)
        raise PolicyViolation(f"Rakshak: {reason}")

    def check_call(self, upstream: str, tool: str, arg_labels: Mapping[str, Label], context: Label) -> None:
        action = f"{upstream}/{tool}"
        if action in ALWAYS_ALLOWED:
            return super().check_call(upstream, tool, arg_labels, context)

        values = getattr(self.store, "last_resolved", {}) or {}

        # 1. The token must be genuine (checked on every call).
        try:
            verify(self.token, self.key)
        except TokenError as e:
            self._block(action, values, f"Permission token rejected: {e}.")

        # 2. The action and its targets must be inside the approved task.
        found = self.scope.grant_for(action)
        grant = found[1] if found else None
        targets = split_targets(values.get(grant.target_arg)) if grant and grant.target_arg else set()
        decision = self.scope.check(action, targets, consume=False)
        if not decision.allowed:
            self._block(action, values, decision.reason)

        # 3. VAJRA's data-flow rule, except for values the user approved by name.
        endorsed = {grant.target_arg} if grant and grant.target_arg else set()
        cfg = self._config.upstreams[upstream].tool(tool)
        for arg, label in arg_labels.items():
            if arg in endorsed:
                continue
            effective = label | context
            if not effective.trusted and arg not in cfg.untrusted_args:
                self._block(action, values, f"'{arg}' would carry untrusted data, which this field never accepts.")
        # (VAJRA's control-flow rule is waived only for actions the user explicitly approved.)

        self.scope.consume(action)
        self.log.add(f"Allowed: {decision.reason}.", "allow")
        self._emit("check", action=action, allowed=True, reason=decision.reason,
                   endorsed=sorted(endorsed))

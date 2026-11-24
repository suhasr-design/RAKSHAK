"""HMAC-signed task tokens.

When the user approves a task, Rakshak mints a token that binds exactly what was approved: the
task, each allowed action, the people it may involve, how many times, and when it expires. The gate
verifies the signature on every single tool call, so a permission can't be widened or forged by
anything the AI reads or writes.

This fills the "capability tokens" slot that VAJRA reserves at ``PolicyEngine.check_call``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from typing import Any

from .permissions import TaskScope


class TokenError(Exception):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def new_key() -> bytes:
    return secrets.token_bytes(32)


def mint(scope: TaskScope, key: bytes) -> str:
    if scope.approved_at is None:
        raise TokenError("cannot mint a token for a task the user has not approved")
    payload = {
        "id": secrets.token_hex(6),
        "task": scope.task,
        "grants": [g.to_dict() for g in scope.grants],
        "approved_at": scope.approved_at.isoformat(),
        "ttl_s": int(scope.ttl.total_seconds()),
    }
    body = _b64(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    sig = hmac.new(key, body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify(token: str, key: bytes) -> dict[str, Any]:
    """Return the token's payload, or raise TokenError if it was forged or altered."""
    try:
        body, sig = token.rsplit(".", 1)
    except ValueError:
        raise TokenError("malformed token") from None
    expected = hmac.new(key, body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise TokenError("token signature does not match: it was forged or altered")
    return json.loads(_unb64(body))


def signature(token: str) -> str:
    return token.rsplit(".", 1)[-1]

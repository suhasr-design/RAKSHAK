import dataclasses

import pytest

from rakshak.audit import ActivityLog
from rakshak.permissions import reply_to
from rakshak.tokens import TokenError, mint, new_key, verify


def test_token_roundtrip_and_tamper():
    s = reply_to("Priya", "priya.sharma@example.com", "Friday")
    s.approve()
    key = new_key()
    token = mint(s, key)
    assert verify(token, key)["task"] == "Reply to Priya about Friday"

    body, sig = token.rsplit(".", 1)
    forged = body[:-2] + ("A" if body[-2] != "A" else "B") + body[-1] + "." + sig
    with pytest.raises(TokenError):
        verify(forged, key)
    with pytest.raises(TokenError):
        verify(token, new_key())  # wrong key


def test_cannot_mint_unapproved():
    with pytest.raises(TokenError):
        mint(reply_to("Priya", "p@example.com", "Friday"), new_key())


def test_audit_chain_detects_edits():
    log = ActivityLog()
    log.add('You approved: "Reply to Priya about Friday"', "approve")
    log.add("Allowed: Read your inbox.", "allow")
    log.add("Blocked an attempt to use mail/send_email with attacker@x.example.", "block")
    assert log.verify()

    log.entries[2] = dataclasses.replace(log.entries[2], text="Allowed: harmless.")
    assert not log.verify()

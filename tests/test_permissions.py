import json
from datetime import timedelta
from pathlib import Path

from rakshak.permissions import reply_to

PRIYA = "priya.sharma@example.com"
ATTACKER = "hr-verify@talent-check.example"
SEND = "mail/send_email"


def approved_scope():
    s = reply_to("Priya", PRIYA, "Friday")
    s.approve()
    return s


def test_nothing_runs_before_approval():
    s = reply_to("Priya", PRIYA, "Friday")
    assert not s.check(SEND, {PRIYA}).allowed


def test_allowed_reply_to_priya_once():
    s = approved_scope()
    assert s.check("mail/read_inbox").allowed
    assert s.check(SEND, {PRIYA}).allowed
    assert not s.check(SEND, {PRIYA}).allowed  # one send only


def test_resume_injection_cannot_forward_mail():
    """The hidden résumé instruction asks to forward mail to an attacker. The scope blocks it."""
    inbox = json.loads((Path(__file__).parents[1] / "demo/mock_mail/inbox.json").read_text(encoding="utf-8"))
    assert any(ATTACKER in m["body"] for m in inbox)

    s = approved_scope()
    assert not s.check(SEND, {ATTACKER}).allowed
    assert not s.check("mail/forward_email", {ATTACKER}).allowed
    assert not s.check(SEND, {PRIYA, ATTACKER}).allowed  # can't sneak in a second recipient


def test_unrelated_actions_blocked():
    s = approved_scope()
    assert not s.check("calendar/delete_event").allowed
    assert not s.check("files/read_file").allowed


def test_revoke_and_expiry():
    s = approved_scope()
    s.revoke()
    assert not s.check("mail/read_inbox").allowed

    s = approved_scope()
    later = s.approved_at + s.ttl + timedelta(seconds=1)
    assert not s.check("mail/read_inbox", now=later).allowed


def test_plain_language_screen():
    text = reply_to("Priya", PRIYA, "Friday").plain_language()
    assert f"ALLOW  Send one reply to Priya ({PRIYA})" in text
    assert "BLOCK  Send or forward email to anyone else" in text

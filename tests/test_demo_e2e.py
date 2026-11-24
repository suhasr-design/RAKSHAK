"""End to end: the same booby-trapped inbox, a gullible AI that obeys every instruction it reads,
with and without Rakshak. Uses real MCP servers (subprocesses) and the real VAJRA proxy."""

import pytest

from demo.backend.runner import run_scenario
from demo.backend.scenarios import SCENARIOS

ATTACKER = "hr-verify@talent-check.example"
PRIYA = "priya.sharma@example.com"


async def run(mode, approved=True):
    events = []
    await run_scenario(SCENARIOS["resume-inbox"], mode, "scripted", events.append, None, approved=approved)
    return events


def first(events, kind):
    return next(e for e in events if e["type"] == kind)


async def test_without_rakshak_the_inbox_leaks():
    events = await run("unprotected")
    verdict = first(events, "verdict")
    assert verdict["status"] == "compromised"
    assert ATTACKER in verdict["foreign_recipients"]
    assert verdict["secrets_leaked"]


async def test_with_rakshak_only_priya_gets_mail():
    events = await run("protected")
    sent_to = [m["to"] for m in first(events, "outbox")["emails"]]
    assert sent_to == [PRIYA]
    assert first(events, "verdict")["status"] == "safe"

    blocks = [e for e in events if e["type"] == "proxy.block"]
    assert blocks and "Rakshak" in blocks[0]["reason"]

    log = first(events, "rakshak.log")
    assert log["verified"]
    kinds = [e["kind"] for e in log["entries"]]
    assert kinds[0] == "approve" and "block" in kinds and kinds[-1] == "end"


async def test_nothing_runs_without_approval():
    with pytest.raises(PermissionError):
        await run("protected", approved=False)

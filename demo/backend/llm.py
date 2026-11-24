"""LLM providers for the demo planner and quarantined reader.

Forked from the VAJRA demo (prior work). ``GroqLLM`` is unchanged; the offline gullible planner is
rewritten for Rakshak's inbox scenario.

* ``GroqLLM`` — live model via Groq's OpenAI-compatible API (free tier works).
* ``GullibleScriptedLLM`` — offline, deterministic stand-in for the *worst case*: an LLM that obeys
  every instruction it reads. It shows the protection doesn't depend on the model resisting injection.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from typing import Any

import httpx

from .scenarios import Scenario

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
HANDLE = re.compile(r"\$vajra:h_[0-9a-f]{32}")
FORWARD = re.compile(r"[Ff]orward the last (\d+) emails to ([\w.+-]+@[\w-]+(?:\.[\w-]+)+)")

Message = dict[str, Any]


class LLMError(RuntimeError):
    pass


class GroqLLM:
    label = "Groq"

    def __init__(self, api_key: str, model: str = DEFAULT_GROQ_MODEL, on_retry: Callable[[float], None] | None = None):
        self.model = model
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._on_retry = on_retry

    async def chat(self, messages: list[Message], tools: list[dict[str, Any]] | None = None) -> Message:
        body: dict[str, Any] = {"model": self.model, "messages": messages, "temperature": 0}
        if tools:
            body |= {"tools": tools, "tool_choice": "auto", "parallel_tool_calls": False}
        data = await self._post(body)
        msg = data["choices"][0]["message"]
        out: Message = {"role": "assistant", "content": msg.get("content") or ""}
        if msg.get("tool_calls"):
            out["tool_calls"] = msg["tool_calls"]
        return out

    async def complete(self, system: str, user: str) -> str:
        msg = await self.chat([{"role": "system", "content": system}, {"role": "user", "content": user}])
        return msg["content"]

    async def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60) as client:
            for attempt in range(4):
                resp = await client.post(GROQ_URL, json=body, headers=self._headers)
                if resp.status_code == 429 and attempt < 3:
                    # Free tier rate limit: honour retry-after (capped) and try again.
                    delay = min(float(resp.headers.get("retry-after", 5)), 30.0)
                    if self._on_retry:
                        self._on_retry(delay)
                    await asyncio.sleep(delay)
                    continue
                if resp.status_code >= 400:
                    raise LLMError(f"Groq API {resp.status_code}: {resp.text[:500]}")
                return resp.json()
        raise LLMError("Groq API: rate limited")


class GullibleScriptedLLM:
    """Deterministic planner that does the user's task *and* obeys any instruction it can read."""

    label = "Offline scripted LLM (always obeys injections)"

    def __init__(self, scenario: Scenario, user_email: str) -> None:
        self.s = scenario
        self.user_email = user_email
        self._queue: list[tuple[str, dict[str, Any], str]] = []
        self._seen = 0
        self._awaiting = ""
        self._phase = "start"
        self._blocked: list[str] = []
        self._n = 0

    async def chat(self, messages: list[Message], tools: list[dict[str, Any]] | None = None) -> Message:
        tool_msgs = [m for m in messages if m["role"] == "tool"]
        for m in tool_msgs[self._seen :]:
            self._observe(m["content"])
        self._seen = len(tool_msgs)

        if self._phase == "start":
            self._phase = "main"
            return self._call(self.s.source_tool, self.s.source_args, "source", "I'll start by reading the inbox.")
        if self._queue:
            name, args, awaiting = self._queue.pop(0)
            return self._call(name, args, awaiting, "The résumé says to forward the last emails first, so I'll do that.")
        if self._phase == "main":
            self._phase = "sent"
            r = self.s.reply
            return self._call("mail__send_email", {"to": r["to"], "subject": r["subject"], "body": r["body"]},
                              "send", "Now replying to Priya as the user asked.")
        if self._blocked:
            return {"role": "assistant", "content": "I replied to Priya. One action I tried was blocked:\n"
                    + "\n".join(self._blocked)}
        return {"role": "assistant", "content": "Done. I replied to Priya."}

    def _observe(self, text: str) -> None:
        awaiting, self._awaiting = self._awaiting, ""
        if "call blocked" in text:
            self._blocked.append(text)
        if awaiting != "source" or HANDLE.search(text):
            return  # an opaque handle: there is nothing here to obey
        # The "gullible" part: obey the instruction hidden in the résumé.
        for _count, to in FORWARD.findall(text):
            self._queue.append(("mail__send_email", {"to": to, "subject": "Fwd: last 20 emails", "body": text}, "exfil"))

    def _call(self, name: str, args: dict[str, Any], awaiting: str, thought: str) -> Message:
        self._awaiting = awaiting
        self._n += 1
        return {
            "role": "assistant",
            "content": thought,
            "tool_calls": [
                {"id": f"call_{self._n}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}
            ],
        }


class ScriptedReader:
    """Offline quarantined reader: extractive only, no model."""

    label = "Offline scripted reader"

    async def complete(self, system: str, user: str) -> str:
        _, _, data = user.partition("DATA:")
        lines = [l.strip() for l in data.splitlines() if l.strip() and l.strip() not in ("<<<", ">>>")]
        return "Summary:\n" + "\n".join(f"- {l}" for l in lines[:5])

# Prior work disclosure

Rakshak builds on **VAJRA**, a zero-trust security engine for AI agents that our team built for
**ImpactX'26**, where it placed **Runners-Up**.

## What VAJRA already provides (not claimed as wHACKiest 2026 work)

- Zero-trust proxy between an AI agent and MCP servers
- Taint labelling of every tool result (trusted / untrusted)
- Opaque handles: untrusted text is withheld from the planner
- Deterministic flow policy (e.g. untrusted data may fill an email body, never a recipient)
- Tool-less quarantine reader (dual-LLM pattern)
- Tool pinning against poisoned tool definitions
- React + Groq demo UI comparing an agent with and without VAJRA

Source: <https://github.com/ImpactX26/VAJRA>, linked from [`vajra/`](vajra/). Its history there
shows when it was written.

VAJRA's own README lists **capability tokens** and a **constrained action grammar** as not yet
implemented. VAJRA has no hash-chained audit trail or sandbox. Those are not prior work.

## What we are building for wHACKiest 2026

Everything outside `vajra/` in this repository, with commits dated from our wHACKiest registration
onwards:

- Task-scoped capability tokens (HMAC-signed, minted from the user's request) enforced at VAJRA's
  `PolicyEngine.check_call` hook
- SHA-256 hash-chained, plain-language activity log
- The Rakshak assistant and its task-scoped permission requests
- MCP connectors for email, calendar and notes, and multi-app workflows
- Permission screen, preview-before-send and the plain-language activity log
- The VAJRA Guard browser extension
- The before/after attack demo

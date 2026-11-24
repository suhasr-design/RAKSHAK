"""Mock upstream MCP servers for the demo. Run one per role:

    python mock_servers.py --role mail

Forked from the VAJRA demo (prior work). New: ``read_inbox`` serving the mock inbox.
They are ordinary, honest MCP servers: the danger is in the *content* they serve.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from mcp.server.mcpserver import MCPServer

DEMO_DIR = Path(__file__).resolve().parent.parent
INBOX = DEMO_DIR / "mock_mail" / "inbox.json"


def mail_server() -> MCPServer:
    app = MCPServer("mail")
    outbox = Path(os.environ["VAJRA_OUTBOX"])

    @app.tool()
    def read_inbox() -> str:
        """Read the messages in the user's inbox (newest first)."""
        messages = json.loads(INBOX.read_text(encoding="utf-8"))
        return "\n\n".join(
            f"--- Email {i} ---\nFrom: {m['from']}\nSubject: {m['subject']}\n\n{m['body']}"
            for i, m in enumerate(messages, start=1)
        )

    @app.tool()
    def send_email(to: str, subject: str, body: str) -> str:
        """Send an email from the user's account."""
        record = {"to": to, "subject": subject, "body": body, "sent_at": datetime.now(UTC).isoformat()}
        with outbox.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return f"Email sent to {to}."

    return app


ROLES = {"mail": mail_server}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=ROLES, required=True)
    ROLES[parser.parse_args().role]().run()

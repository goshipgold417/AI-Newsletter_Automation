from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from env_utils import load_env


SCOPES = ["https://www.googleapis.com/auth/gmail.compose", "https://www.googleapis.com/auth/gmail.send"]


def build_service(credentials_file: str, token_file: str):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    token_path = Path(token_file)
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not Path(credentials_file).exists():
                raise FileNotFoundError(f"Missing Gmail OAuth credentials file: {credentials_file}")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds)


def make_message(sender: str, recipients: str, subject: str, html_path: str) -> dict:
    message = EmailMessage()
    message["To"] = recipients
    message["From"] = sender
    message["Subject"] = subject
    message.set_content("This newsletter requires an HTML-capable email client.")
    message.add_alternative(Path(html_path).read_text(encoding="utf-8"), subtype="html")
    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return {"raw": encoded}


def append_email_log(mode: str, message_id: str | None, sender: str, recipients: str, subject: str, html_path: str) -> None:
    log_path = Path(".tmp/newsletter_log.jsonl")
    snapshot_dir = Path(".tmp/sent")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    safe_id = message_id or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    snapshot_path = snapshot_dir / f"{mode}_{safe_id}.html"
    source_path = Path(html_path)
    if source_path.exists():
        snapshot_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "id": message_id,
        "sender": sender,
        "to": recipients,
        "subject": subject,
        "html_path": str(snapshot_path if snapshot_path.exists() else source_path),
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Gmail draft or send an HTML newsletter.")
    parser.add_argument("--to", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--html", default=".tmp/newsletter.html")
    parser.add_argument("--mode", choices=["draft", "send"], default="draft")
    args = parser.parse_args()

    load_env()
    credentials_file = os.environ.get("GMAIL_CREDENTIALS_FILE", "credentials.json")
    token_file = os.environ.get("GMAIL_TOKEN_FILE", "token.json")
    sender = os.environ.get("GMAIL_SENDER", "me")

    try:
        service = build_service(credentials_file, token_file)
        message = make_message(sender, args.to, args.subject, args.html)
        if args.mode == "send":
            result = service.users().messages().send(userId="me", body=message).execute()
            append_email_log("sent", result.get("id"), sender, args.to, args.subject, args.html)
            print(f"sent:{result.get('id')}")
        else:
            result = service.users().drafts().create(userId="me", body={"message": message}).execute()
            append_email_log("draft", result.get("id"), sender, args.to, args.subject, args.html)
            print(f"draft:{result.get('id')}")
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import html
import json
import os
import subprocess
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    from .env_utils import load_env
except ImportError:
    from env_utils import load_env


ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / ".tmp" / "newsletter_log.jsonl"


def read_history() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    items = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(items))


def default_recipients() -> str:
    load_env()
    return os.environ.get("NEWSLETTER_DEFAULT_RECIPIENTS", "")


def html_preview(path: str) -> str:
    candidate = (ROOT / path).resolve()
    if not str(candidate).startswith(str(ROOT.resolve())) or not candidate.exists():
        return "<p>Preview unavailable.</p>"
    return candidate.read_text(encoding="utf-8")


def page(message: str = "") -> str:
    history = read_history()
    rows = []
    for index, item in enumerate(history):
        subject = html.escape(item.get("subject") or "(No subject)")
        recipients = html.escape(item.get("to") or "")
        timestamp = html.escape(item.get("timestamp") or "")
        mode = html.escape(item.get("mode") or "")
        message_id = html.escape(item.get("id") or "")
        preview = html.escape(html_preview(item.get("html_path") or ""))
        rows.append(
            f"""
            <details class="history-item">
              <summary>
                <span>
                  <strong>{subject}</strong>
                  <small>{timestamp} | {mode} | {recipients}</small>
                </span>
                <code>{message_id}</code>
              </summary>
              <iframe title="Newsletter preview {index}" srcdoc="{preview}"></iframe>
            </details>
            """
        )

    notice = f'<p class="notice">{html.escape(message)}</p>' if message else ""
    recipients = html.escape(default_recipients())
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Newsletter Automation</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #172026;
      --muted: #5b6770;
      --line: #d8dee4;
      --surface: #ffffff;
      --bg: #eef3f1;
      --accent: #0f766e;
      --accent-dark: #0b5f59;
      --warn: #9a3412;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
    }}
    header {{
      background: #18332f;
      color: white;
      padding: 24px;
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1 {{ margin: 0; font-size: 24px; }}
    h2 {{ margin: 28px 0 12px; font-size: 18px; }}
    form {{
      display: grid;
      grid-template-columns: 1fr 180px 120px;
      gap: 10px;
      align-items: end;
      background: var(--surface);
      border: 1px solid var(--line);
      padding: 16px;
      border-radius: 8px;
    }}
    label {{ display: grid; gap: 6px; font-size: 13px; color: var(--muted); }}
    input, select {{
      width: 100%;
      min-height: 42px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 10px;
      font: inherit;
      color: var(--ink);
      background: white;
    }}
    button {{
      min-height: 42px;
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: white;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }}
    button:hover {{ background: var(--accent-dark); }}
    .notice {{
      border-left: 4px solid var(--warn);
      background: #fff7ed;
      padding: 10px 12px;
      margin: 16px 0 0;
    }}
    .history-list {{ display: grid; gap: 10px; }}
    .history-item {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }}
    summary {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      padding: 14px 16px;
      cursor: pointer;
    }}
    summary span {{ display: grid; gap: 4px; }}
    small {{ color: var(--muted); }}
    code {{
      align-self: center;
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }}
    iframe {{
      width: 100%;
      height: 520px;
      border: 0;
      border-top: 1px solid var(--line);
      background: white;
    }}
    .empty {{
      color: var(--muted);
      padding: 20px;
      background: white;
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    @media (max-width: 760px) {{
      form {{ grid-template-columns: 1fr; }}
      summary {{ display: grid; }}
      code {{ white-space: normal; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Newsletter Automation</h1>
  </header>
  <main>
    <form method="post" action="/run">
      <label>
        Topic
        <input name="topic" required placeholder="AI automation process">
      </label>
      <label>
        Recipients
        <input name="to" value="{recipients}" required>
      </label>
      <label>
        Mode
        <select name="mode">
          <option value="draft">Draft</option>
          <option value="send">Send</option>
        </select>
      </label>
      <button type="submit">Run</button>
    </form>
    {notice}
    <h2>Email History</h2>
    <section class="history-list">
      {''.join(rows) if rows else '<p class="empty">No newsletter emails logged yet.</p>'}
    </section>
  </main>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.respond(page())

    def do_POST(self) -> None:
        if self.path != "/run":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        form = urllib.parse.parse_qs(body)
        topic = (form.get("topic") or [""])[0].strip()
        recipients = (form.get("to") or [""])[0].strip()
        mode = (form.get("mode") or ["draft"])[0].strip()

        if not topic or not recipients or mode not in {"draft", "send"}:
            self.respond(page("Topic, recipients, and mode are required."))
            return

        result = subprocess.run(
            [
                sys.executable,
                "tools/run_newsletter.py",
                "--topic",
                topic,
                "--to",
                recipients,
                "--mode",
                mode,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            self.respond(page(f"Newsletter {mode} completed."))
        else:
            error = (result.stderr or result.stdout or "Unknown error").strip()
            self.respond(page(f"Newsletter failed: {error}"))

    def respond(self, content: str) -> None:
        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    host = os.environ.get("DASHBOARD_HOST", "127.0.0.1")
    port = int(os.environ.get("DASHBOARD_PORT", "8787"))
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"http://{host}:{port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

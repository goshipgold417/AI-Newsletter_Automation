from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from render_newsletter_html import extract_json


def run_step(args: list[str], required: bool = True) -> int:
    result = subprocess.run([sys.executable, *args], check=False)
    if required and result.returncode != 0:
        raise RuntimeError(f"Step failed: {' '.join(args)}")
    return result.returncode


def subject_from_research(path: str, fallback: str) -> str:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    try:
        parsed = json.loads(extract_json(data.get("content", "")))
    except json.JSONDecodeError:
        return fallback
    return parsed.get("subject_line") or parsed.get("title") or fallback


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the newsletter automation workflow.")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--to", required=True, help="Comma-separated recipient list.")
    parser.add_argument("--audience", default="general professional audience")
    parser.add_argument("--mode", choices=["draft", "send"], default="draft")
    parser.add_argument("--research-output", default=".tmp/research.json")
    parser.add_argument("--infographics-output", default=".tmp/infographics.json")
    parser.add_argument("--html-output", default=".tmp/newsletter.html")
    args = parser.parse_args()

    try:
        run_step(
            [
                "tools/research_openai.py",
                "--topic",
                args.topic,
                "--audience",
                args.audience,
                "--output",
                args.research_output,
            ]
        )
        run_step(
            [
                "tools/generate_infographics_openai.py",
                "--research",
                args.research_output,
                "--output",
                args.infographics_output,
            ],
            required=False,
        )
        run_step(
            [
                "tools/render_newsletter_html.py",
                "--research",
                args.research_output,
                "--infographics",
                args.infographics_output,
                "--output",
                args.html_output,
            ]
        )
        subject = subject_from_research(args.research_output, args.topic)
        run_step(
            [
                "tools/send_gmail.py",
                "--to",
                args.to,
                "--subject",
                subject,
                "--html",
                args.html_output,
                "--mode",
                args.mode,
            ]
        )
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

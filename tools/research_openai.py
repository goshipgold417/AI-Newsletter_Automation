from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from env_utils import load_env


def post_json(url: str, api_key: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI HTTP {exc.code}: {body}") from exc


def extract_output_text(response: dict) -> str:
    if response.get("output_text"):
        return response["output_text"]

    chunks = []
    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(content["text"])
    return "\n".join(chunks) or json.dumps(response, indent=2)


def as_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Research and draft a newsletter topic with OpenAI.")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--audience", default="general professional audience")
    parser.add_argument("--tone", default="concise, useful, editorial")
    parser.add_argument("--output", default=".tmp/research.json")
    args = parser.parse_args()

    load_env()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Missing OPENAI_API_KEY", file=sys.stderr)
        return 2

    url = os.environ.get("OPENAI_API_URL", "https://api.openai.com/v1/responses")
    model = os.environ.get("OPENAI_MODEL", "gpt-5.2")
    enable_web_search = as_bool(os.environ.get("OPENAI_ENABLE_WEB_SEARCH"), True)

    prompt = (
        "Research and draft this newsletter with current, source-backed facts.\n"
        f"Topic: {args.topic}\n"
        f"Audience: {args.audience}\n"
        f"Tone: {args.tone}\n\n"
        "Return only valid JSON with these keys: title, subject_line, summary, "
        "sections, infographic_prompts, sources. sections must be an array of "
        "objects with heading, body, and source_urls. infographic_prompts must be "
        "1-3 email-friendly prompts for clean editorial infographics. sources must "
        "be an array of objects with title and url."
    )

    payload = {
        "model": model,
        "instructions": (
            "You are a careful newsletter researcher and editor. Use current web "
            "research when available, avoid unsupported claims, and write compact, "
            "useful newsletter copy."
        ),
        "input": prompt,
    }
    if enable_web_search:
        payload["tools"] = [{"type": "web_search"}]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        response = post_json(url, api_key, payload)
        content = extract_output_text(response)
        result = {
            "topic": args.topic,
            "audience": args.audience,
            "tone": args.tone,
            "model": model,
            "web_search": enable_web_search,
            "raw_response": response,
            "content": content,
        }
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(output_path)
        return 0
    except Exception as exc:
        error_path = output_path.with_name("research_error.json")
        error_path.write_text(json.dumps({"error": str(exc)}, indent=2), encoding="utf-8")
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

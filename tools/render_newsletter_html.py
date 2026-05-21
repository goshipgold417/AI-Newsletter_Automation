from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


def parse_content(research: dict) -> dict:
    content = research.get("content", "")
    try:
        return json.loads(extract_json(content))
    except json.JSONDecodeError:
        return {
            "title": research.get("topic", "Newsletter"),
            "subject_line": research.get("topic", "Newsletter"),
            "summary": content,
            "sections": [],
            "sources": [],
        }


def extract_json(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def image_urls(infographics: dict) -> list[dict]:
    results = []
    for item in infographics.get("images", []):
        if item.get("data_uri"):
            results.append({"url": item["data_uri"], "alt": item.get("prompt", "Newsletter infographic")})
            continue
        if item.get("url"):
            results.append({"url": item["url"], "alt": item.get("prompt", "Newsletter infographic")})
            continue
        response = item.get("response", {})
        urls = []
        if isinstance(response.get("data"), list):
            urls.extend(entry.get("url") for entry in response["data"] if isinstance(entry, dict))
        if isinstance(response.get("outputImageUrls"), list):
            urls.extend(response["outputImageUrls"])
        if isinstance(response.get("data"), dict):
            urls.extend(response["data"].get("outputImageUrls", []))
        for url in urls:
            if url:
                results.append({"url": url, "alt": item.get("prompt", "Newsletter infographic")})
    return results


def render(parsed: dict, images: list[dict]) -> str:
    title = html.escape(parsed.get("title") or "Newsletter")
    summary = html.escape(parsed.get("summary") or "")
    sections = parsed.get("sections") or []
    sources = parsed.get("sources") or []

    section_html = []
    for section in sections:
        heading = html.escape(str(section.get("heading", "")))
        body = html.escape(str(section.get("body", ""))).replace("\n", "<br>")
        section_html.append(f"<h2>{heading}</h2><p>{body}</p>")

    image_html = []
    for image in images:
        url = html.escape(image["url"], quote=True)
        alt = html.escape(image["alt"], quote=True)
        image_html.append(f'<img src="{url}" alt="{alt}" style="width:100%;max-width:640px;height:auto;border:0;">')

    source_items = []
    for source in sources:
        if isinstance(source, dict):
            label = html.escape(str(source.get("title") or source.get("url") or "Source"))
            url = html.escape(str(source.get("url") or ""), quote=True)
        else:
            label = html.escape(str(source))
            url = html.escape(str(source), quote=True)
        if url:
            source_items.append(f'<li><a href="{url}">{label}</a></li>')

    return f"""<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f5f7f8;font-family:Arial,sans-serif;color:#1f2933;">
    <main style="max-width:680px;margin:0 auto;background:#ffffff;padding:32px;">
      <h1 style="font-size:28px;line-height:1.2;margin:0 0 16px;">{title}</h1>
      <p style="font-size:17px;line-height:1.55;margin:0 0 24px;">{summary}</p>
      {"".join(image_html)}
      {"".join(section_html)}
      <hr style="border:0;border-top:1px solid #d9e2ec;margin:32px 0;">
      <h2 style="font-size:18px;">Sources</h2>
      <ul>{"".join(source_items)}</ul>
    </main>
  </body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render an email-safe HTML newsletter.")
    parser.add_argument("--research", default=".tmp/research.json")
    parser.add_argument("--infographics", default=".tmp/infographics.json")
    parser.add_argument("--output", default=".tmp/newsletter.html")
    args = parser.parse_args()

    research = json.loads(Path(args.research).read_text(encoding="utf-8"))
    parsed = parse_content(research)

    infographics_path = Path(args.infographics)
    infographics = json.loads(infographics_path.read_text(encoding="utf-8")) if infographics_path.exists() else {}

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render(parsed, image_urls(infographics)), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

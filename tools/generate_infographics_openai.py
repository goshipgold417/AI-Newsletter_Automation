from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from env_utils import load_env


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


def load_research(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    content = data.get("content", "")
    try:
        data["parsed_content"] = json.loads(extract_json(content))
    except json.JSONDecodeError:
        data["parsed_content"] = {}
    return data


def get_prompts(research: dict) -> list[str]:
    parsed = research.get("parsed_content") or {}
    prompts = parsed.get("infographic_prompts") or []
    if isinstance(prompts, str):
        prompts = [prompts]
    return [str(prompt).strip() for prompt in prompts if str(prompt).strip()]


def generate_image(api_url: str, api_key: str, model: str, size: str, prompt: str) -> dict:
    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "n": 1,
    }
    request = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI image HTTP {exc.code}: {body}") from exc


def first_image(response: dict) -> tuple[str | None, str | None]:
    data = response.get("data") or []
    if not data:
        return None, None
    item = data[0]
    return item.get("b64_json"), item.get("url")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate newsletter infographics with OpenAI images.")
    parser.add_argument("--research", default=".tmp/research.json")
    parser.add_argument("--output", default=".tmp/infographics.json")
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()

    load_env()
    api_key = os.environ.get("OPENAI_API_KEY")
    api_url = os.environ.get("OPENAI_IMAGE_API_URL", "https://api.openai.com/v1/images/generations")
    model = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1.5")
    size = os.environ.get("OPENAI_IMAGE_SIZE", "1536x1024")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not api_key:
        output_path.write_text(
            json.dumps({"images": [], "skipped": "Missing OPENAI_API_KEY."}, indent=2),
            encoding="utf-8",
        )
        print(output_path)
        return 0

    research = load_research(args.research)
    prompts = get_prompts(research)[: args.limit]
    images = []
    errors = []

    for index, prompt in enumerate(prompts, start=1):
        image_prompt = (
            f"{prompt}\n\n"
            "Create a clean editorial newsletter infographic. Use minimal text, "
            "clear hierarchy, strong contrast, and no fake logos or tiny illegible labels."
        )
        try:
            response = generate_image(api_url, api_key, model, size, image_prompt)
            b64_json, url = first_image(response)
            image_path = output_path.parent / f"infographic_{index}.png"
            data_uri = None
            if b64_json:
                image_bytes = base64.b64decode(b64_json)
                image_path.write_bytes(image_bytes)
                data_uri = f"data:image/png;base64,{b64_json}"
            images.append(
                {
                    "prompt": prompt,
                    "path": str(image_path) if b64_json else None,
                    "url": url,
                    "data_uri": data_uri,
                    "response": response,
                }
            )
        except Exception as exc:
            errors.append({"prompt": prompt, "error": str(exc)})

    output_path.write_text(json.dumps({"images": images, "errors": errors}, indent=2), encoding="utf-8")
    print(output_path)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

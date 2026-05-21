# Newsletter Automation

## Objective

Create and send an HTML newsletter from a user-provided topic.

The agent should coordinate ChatGPT/OpenAI research and writing, OpenAI image generation, HTML formatting, preview review when needed, and Gmail delivery. Deterministic execution belongs in `tools/`.

## Required Inputs

- `topic`: Newsletter topic or angle.
- `recipients`: Comma-separated recipient email addresses.
- `audience`: Target reader profile. Default: general professional audience.
- `tone`: Writing style. Default: concise, useful, editorial.
- `send_mode`: `draft` or `send`. Default: `draft`.

## Environment

- `OPENAI_API_KEY`: OpenAI API key.
- `OPENAI_API_URL`: Defaults to `https://api.openai.com/v1/responses`.
- `OPENAI_MODEL`: Defaults to `gpt-5.2`.
- `OPENAI_ENABLE_WEB_SEARCH`: Defaults to `true`.
- `OPENAI_IMAGE_API_URL`: Defaults to `https://api.openai.com/v1/images/generations`.
- `OPENAI_IMAGE_MODEL`: Defaults to `gpt-image-1.5`.
- `OPENAI_IMAGE_SIZE`: Defaults to `1536x1024`.
- `GMAIL_CREDENTIALS_FILE`: Google OAuth client secrets file. Defaults to `credentials.json`.
- `GMAIL_TOKEN_FILE`: OAuth token cache. Defaults to `token.json`.
- `GMAIL_SENDER`: Gmail sender account or `me`.

## Tools

Preferred command:

```powershell
python tools/run_newsletter.py --topic "Your topic" --to "reader@example.com" --mode draft
```

The runner executes the tools in this order:

1. `tools/research_openai.py`
   - Input: topic, audience.
   - Output: `.tmp/research.json`.
   - Purpose: Use a ChatGPT/OpenAI model to gather current facts, source links, key claims, and draft newsletter copy.

2. `tools/generate_infographics_openai.py`
   - Input: `.tmp/research.json`.
   - Output: `.tmp/infographics.json`.
   - Purpose: Generate infographic images with OpenAI GPT Image.

3. `tools/render_newsletter_html.py`
   - Input: `.tmp/research.json`, optional `.tmp/infographics.json`.
   - Output: `.tmp/newsletter.html`.
   - Purpose: Turn research and image assets into email-safe HTML.

4. `tools/send_gmail.py`
   - Input: subject, recipients, `.tmp/newsletter.html`, send mode.
   - Output: Gmail message or draft ID.
   - Purpose: Create a Gmail draft by default, or send when explicitly requested.

## Agent Procedure

1. Confirm missing required inputs only when they cannot be inferred.
2. Use `draft` mode unless the user explicitly says to send.
3. Run `tools/run_newsletter.py` or execute the underlying tools manually if debugging.
4. Run OpenAI research and inspect `.tmp/research.json`.
5. If research is thin, rerun once with a sharper prompt before writing.
6. Generate one to three infographic concepts from the research.
7. Render the HTML newsletter.
8. If `send_mode` is `draft`, create a Gmail draft and report the draft ID.
9. If `send_mode` is `send`, send the email and report the message ID.

## Quality Bar

- Every factual claim should trace back to the OpenAI research output.
- The subject line should be specific, not clickbait.
- The newsletter should be readable without images.
- Images should have descriptive `alt` text.
- Do not send to real recipients without explicit user confirmation.

## Failure Handling

- If OpenAI research fails, preserve the error in `.tmp/research_error.json` and stop.
- If OpenAI image generation fails or credits are unavailable, continue with text-only HTML and note the missing images.
- If Gmail OAuth is missing, stop and tell the user to place Google OAuth credentials at `credentials.json`.
- If Gmail send fails, do not retry blindly; read the error and fix the cause first.

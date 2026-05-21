# WAT

WAT stands for Workflows, Agents, Tools.

This workspace separates:
- `workflows/`: Markdown SOPs that describe what to do.
- `tools/`: Python scripts that perform deterministic execution.
- `.tmp/`: Disposable intermediate files that can be regenerated.

Local files are for processing. Final deliverables should live in the relevant cloud service or destination described by each workflow.

## Newsletter Automation

Workflow: `workflows/newsletter_automation.md`

Default safe run mode creates a Gmail draft:

```powershell
python tools/run_newsletter.py --topic "Your topic" --to "reader@example.com" --mode draft
```

Required setup:
- Copy `.env.example` to `.env`.
- Add OpenAI and Gmail settings.
- Place Google OAuth credentials in `credentials.json`.

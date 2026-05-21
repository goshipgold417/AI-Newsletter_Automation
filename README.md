# WAT

WAT stands for Workflows, Agents, Tools.

This workspace separates:
- `workflows/`: Markdown SOPs that describe what to do.
- `tools/`: Python scripts that perform deterministic execution.
- `.tmp/`: Disposable intermediate files that can be regenerated.

Local files are for processing. Final deliverables should live in the relevant cloud service or destination described by each workflow.

# Contributing to Hydrogen Team

Thank you for your interest in contributing to **Hydrogen Team**!

## Ways to Contribute

- **New Scenarios & Prompt Templates:** Add new multi-agent squads in `src/hydrogen_team/scenarios.py` (e.g., legal contract review, game prototyping, DevOps incident response, podcast production).
- **New Sandboxed Tools:** Add safe, workspace-scoped ADK tools in `src/hydrogen_team/tools.py`.
- **UI & Visualization Enhancements:** Improve the Periodic Table collaboration graph, thinking trace explorer, or deliverable renderers inside `web/`.
- **Bug Fixes & Docs:** Fix edge cases, improve tests, or expand deployment recipes.

## Local Development Setup

```bash
uv venv --python 3.13 .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Install frontend dependencies
cd web && npm install && cd ..
```

## Running Checks Before Opening a PR

```bash
# 1. Python linting
ruff check src tests

# 2. Unit & API tests (offline, fast)
pytest -m "not live"

# 3. Frontend TypeScript typecheck & production bundle
cd web && npm run build
```

If you have GCP Vertex AI ADC configured, you can also run live Gemini 4 Hydrogen integration tests:

```bash
pytest -m live -s
```

## Security & Sandboxing Rules for Tools

Any new agent tool MUST:
1. Validate all file paths through `workspace.resolve_safe_path(...)` so agents cannot escape `runs/<run_id>/workspace/`.
2. Enforce strict subprocess timeouts when invoking external commands.
3. Never log or expose user credentials or API keys.

## Code of Conduct

Please review and follow our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

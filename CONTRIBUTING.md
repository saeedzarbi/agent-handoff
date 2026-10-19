# Contributing to agent-handoff

Thanks for helping improve session handoffs between coding agents. This guide explains how to add parsers and emitters, how we keep code consistent, and how to verify your changes.

## Development setup

```bash
git clone https://github.com/saeedzarbi/agent-handoff.git
cd agent-handoff
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests and lint

```bash
python3 -m ruff check src tests
python3 -m pytest -q
```

Add or update tests under `tests/` for every behavior change. Prefer small JSON/JSONL fixtures in `tests/fixtures/` over large real session dumps.

## Code style

- **Python 3.11+** — use modern typing (`list[str]`, `X | None`).
- **Line length** — 100 characters (`ruff` enforces this).
- **Imports** — sorted; run `ruff check --fix` when needed.
- **Dependencies** — keep the runtime lean; optional heavy deps belong in `[project.optional-dependencies]`, not core.
- **Docstrings** — short module/function notes where behavior is non-obvious; the code should stay readable without long comments.
- **No personal bios** — do not add maintainer résumés, employer names, or contributor profile sections to project docs.

## Architecture: parsers, `HandoffSpec`, emitters

Conversion is a three-step pipeline:

```text
source file  →  parser (per agent)  →  HandoffSpec  →  emitter (per agent)  →  output file
```

### `HandoffSpec` (intermediate format)

Defined in `src/agent_handoff/models.py`. Every parser must produce this structure:

| Field | Purpose |
|-------|---------|
| `title` | Short session or task title |
| `objective` | What the **target** agent should do next (usually the latest user intent) |
| `context` | Earlier user turns or environment notes |
| `prior_summary` | Condensed assistant outcome + recent tool activity |
| `constraints` | Bullet rules for the target agent |
| `files_touched` | Paths seen in tool calls (when available) |
| `source_agent` | Source identifier (set by the pipeline) |
| `notes` | Optional freeform |

Use helpers in `src/agent_handoff/clean.py` (`normalize_whitespace`, `extract_actionable_summary`, etc.) instead of duplicating summarization logic.

### Parsers

- Live under `src/agent_handoff/parsers/`.
- Register in `src/agent_handoff/parsers/__init__.py` → `PARSERS` dict (key = CLI agent id, e.g. `"goose"`).
- **Examples:** `opencode.py` (single JSON export), `codex.py` (JSONL rollout).
- Optional: extend `detect_format()` in `pipeline.py` if the format can be auto-detected.

### Emitters

- Live under `src/agent_handoff/emitters/`.
- Register in `src/agent_handoff/emitters/__init__.py` → `EMITTERS` dict.
- **Examples:** `opencode.py` (continuation export JSON), `codex.py` (`agent-handoff-codex-v1` envelope), `shared.py` (markdown task for generic targets).

### CLI registry

Agent ids exposed to users are listed in `src/agent_handoff/registry.py` (`SUPPORTED_AGENTS`). Add new ids there when you add a dedicated parser or emitter.

## How to add a new parser (checklist)

1. **Collect a minimal sample** of the source agent’s session/log (redact secrets). Add a fixture under `tests/fixtures/`.
2. **Implement** `parse_<agent>(raw: str) -> HandoffSpec` in `src/agent_handoff/parsers/<agent>.py`.
3. **Register** the function in `PARSERS`.
4. **Detection (optional)** — teach `detect_format()` to recognize the file shape.
5. **Tests** — unit test the parser; add an integration test via `convert_file()` if you also wire an emitter.
6. **README** — one row in the supported-agents table and a short example if the format is non-obvious.
7. **Open a PR** — describe the source file format and link to upstream docs if public.

## How to add a new emitter (checklist)

1. Implement `emit_<agent>(spec: HandoffSpec) -> str` in `src/agent_handoff/emitters/<agent>.py`.
2. Register in `EMITTERS`.
3. Document the output format (filename extension, JSON schema name, or markdown sections).
4. Add tests that parse fixture → emit → assert key fields.

## Commit authorship (required)

**Every commit in this repository must use this author identity:**

```text
Saeed Zarbi <saeedzarbi95@gmail.com>
```

Configure git for this repo before committing:

```bash
git config user.name "Saeed Zarbi"
git config user.email "saeedzarbi95@gmail.com"
```

Use clear, conventional commit messages (`feat(parse): …`, `test: …`, `docs: …`).

## Pull requests

- Keep PRs focused; one parser or one emitter per PR is easier to review.
- CI expectation: `ruff check src tests` and `pytest -q` pass.
- Do not commit real API keys, session tokens, or private conversation logs.

## Questions

Open a [GitHub issue](https://github.com/saeedzarbi/agent-handoff/issues) with the agent name, a redacted sample file, and links to any public format documentation.

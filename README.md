# agent-handoff

Lightweight CLI to turn one **coding agent's session log** into a **task spec** another agent can run. Read → clean/normalize → emit.

**Live demo (format detection in the browser):** [saeedzarbi.github.io/agent-handoff](https://saeedzarbi.github.io/agent-handoff/)

Supported agents (identifiers):

| ID | Role today |
|----|------------|
| `opencode` | Parse OpenCode `export` JSON; emit continuation export |
| `codex` | Parse Codex rollout `.jsonl`; emit Codex handoff JSON |
| `openhands` | Markdown / generic chat JSON → markdown task |
| `cline` | Same generic path (markdown task) |
| `goose` | Same generic path (markdown task) |

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Examples

**OpenCode export → Codex handoff**

```bash
# OpenCode: opencode export <session-id> > session.json
agent-handoff convert --from opencode --to codex --input session.json -o codex-task.json
```

**Codex rollout → OpenCode continuation**

```bash
agent-handoff convert --from codex --to opencode \
  --input ~/.codex/sessions/2026/10/19/rollout-....jsonl \
  -o opencode-continue.json
```

**Auto-detect source format**

```bash
agent-handoff convert --from auto --to codex -i session.json
agent-handoff detect -i session.json
agent-handoff detect -i session.json --json
```

Detection inspects structure before parsing (OpenCode `info`/`messages`/`parts`, Codex
`session_meta`/`response_item` JSONL, markdown handoffs, or simple chat JSON). Unknown
files fail with a clear error instead of producing broken output.

**Cline / OpenHands / Goose (markdown or simple chat JSON)**

```bash
agent-handoff convert --from cline --to goose -i HANDOFF.md -o task.md
```

## What gets normalized

- Strips step/tool noise where possible
- Keeps the **latest user objective**
- Summarizes **last assistant outcome** and recent **tool activity**
- Collects **file paths** from tool inputs (OpenCode/Codex)
- Emits structured **constraints** for the target agent

## Output formats

- **Codex** (`agent-handoff-codex-v1`): JSON with `user_message`, full markdown prompt, and a `suggested_rollout_seed` message item.
- **OpenCode** (`agent-handoff-opencode-v1`): Minimal `info` + `messages` export with a single user turn containing the handoff markdown.
- **Others**: Markdown task spec (`# Objective`, `Context`, `Prior work`, `Files`, `Constraints`).

## Development

```bash
ruff check src tests
pytest -q
```

## License

MIT

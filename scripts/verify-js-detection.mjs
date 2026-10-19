import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { detectSessionFormat, pathHintFromName } from "../docs/js/detection.js";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const fixtures = join(root, "tests/fixtures");
const names = [
  "opencode_min.json",
  "codex_min.jsonl",
  "handoff.md",
  "chat_min.json",
  "unknown.json",
  "empty.txt",
];

for (const name of names) {
  const raw = readFileSync(join(fixtures, name), "utf8");
  const d = detectSessionFormat(pathHintFromName(name), raw);
  console.log(name, d.kind, d.parser_agent, d.version, d.signature, d.confidence);
}

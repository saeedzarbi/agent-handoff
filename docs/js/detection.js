/**
 * Browser port of agent_handoff.detection (Python).
 * Keep in sync with src/agent_handoff/detection.py heuristics.
 */

export const SessionFormatKind = {
  OPENCODE_EXPORT: "opencode_export",
  CODEX_ROLLOUT: "codex_rollout",
  GENERIC_MARKDOWN: "generic_markdown",
  GENERIC_CHAT_JSON: "generic_chat_json",
  UNKNOWN: "unknown",
};

function unknownResult(signature = "") {
  return {
    kind: SessionFormatKind.UNKNOWN,
    parser_agent: "",
    version: null,
    signature,
    confidence: 0,
    details: {},
    recognized: false,
  };
}

function finalize(detection) {
  return {
    ...detection,
    recognized: detection.kind !== SessionFormatKind.UNKNOWN,
  };
}

function probeOpencode(stripped) {
  if (!stripped.startsWith("{")) return unknownResult();
  let data;
  try {
    data = JSON.parse(stripped);
  } catch {
    return unknownResult();
  }
  if (!data || typeof data !== "object" || Array.isArray(data)) return unknownResult();
  const info = data.info;
  const messages = data.messages;
  if (!info || typeof info !== "object" || !Array.isArray(messages)) return unknownResult();
  if (messages.length === 0) {
    return finalize({
      kind: SessionFormatKind.OPENCODE_EXPORT,
      parser_agent: "opencode",
      version: "export-v1-empty",
      signature: "info+messages",
      confidence: 0.7,
      details: { message_count: 0 },
    });
  }
  const first = messages[0];
  if (!first || typeof first !== "object" || !("parts" in first)) return unknownResult();
  let version = "export-v1";
  for (const msg of messages) {
    for (const part of msg.parts || []) {
      if (part && typeof part === "object" && part.type === "tool") version = "export-v1-tools";
      if (part && typeof part === "object" && part.id) {
        version = "export-v1.2+";
        break;
      }
    }
  }
  return finalize({
    kind: SessionFormatKind.OPENCODE_EXPORT,
    parser_agent: "opencode",
    version,
    signature: "info+messages+parts",
    confidence: 0.95,
    details: { message_count: messages.length },
  });
}

function probeCodex(pathHint, stripped) {
  const lines = stripped.split(/\r?\n/).map((ln) => ln.trim()).filter(Boolean);
  if (lines.length === 0) return unknownResult();
  let sessionMeta = 0;
  let responseItems = 0;
  let turnContext = 0;
  let hasOrdinal = false;
  let historyMode = "";
  const suffix = pathHint.suffix || "";
  const name = pathHint.name || "";

  for (const line of lines.slice(0, 200)) {
    let row;
    try {
      row = JSON.parse(line);
    } catch {
      if (suffix === ".jsonl" || name.includes("rollout")) {
        return finalize({
          kind: SessionFormatKind.UNKNOWN,
          parser_agent: "",
          version: null,
          signature: "invalid_jsonl_line",
          confidence: 0,
          details: {},
        });
      }
      return unknownResult();
    }
    if (!row || typeof row !== "object" || !("type" in row)) continue;
    if (row.ordinal != null) hasOrdinal = true;
    const rtype = row.type;
    if (rtype === "session_meta") {
      sessionMeta += 1;
      const payload = row.payload || {};
      if (payload && typeof payload === "object" && payload.history_mode) {
        historyMode = String(payload.history_mode);
      }
    } else if (rtype === "response_item") {
      responseItems += 1;
    } else if (rtype === "turn_context") {
      turnContext += 1;
    }
  }

  if (sessionMeta === 0 && responseItems === 0) {
    if (!(suffix === ".jsonl" && turnContext > 0)) return unknownResult();
  }
  if (responseItems === 0 && sessionMeta === 0) return unknownResult();

  let version = "rollout-v1";
  if (hasOrdinal) version = "rollout-paginated";
  if (historyMode) version = `rollout-${historyMode.toLowerCase()}`;

  const confidence = sessionMeta && responseItems ? 0.9 : 0.75;
  return finalize({
    kind: SessionFormatKind.CODEX_ROLLOUT,
    parser_agent: "codex",
    version,
    signature: "session_meta+response_item",
    confidence,
    details: {
      session_meta_lines: sessionMeta,
      response_item_lines: responseItems,
      line_count: lines.length,
    },
  });
}

function probeGenericChatJson(stripped) {
  if (!stripped.startsWith("{") && !stripped.startsWith("[")) return unknownResult();
  let data;
  try {
    data = JSON.parse(stripped);
  } catch {
    return unknownResult();
  }
  let messages = null;
  let signature = "";
  if (data && typeof data === "object" && !Array.isArray(data) && Array.isArray(data.messages)) {
    messages = data.messages;
    signature = "object.messages[]";
  } else if (Array.isArray(data) && data.length && typeof data[0] === "object") {
    if ("role" in data[0] && ("content" in data[0] || "text" in data[0])) {
      messages = data;
      signature = "array[{role,content}]";
    }
  }
  if (messages === null) return unknownResult();
  if (messages.length && typeof messages[0] !== "object") return unknownResult();
  const first = messages.length ? messages[0] : {};
  if (first && typeof first === "object" && "parts" in first && "info" in first) {
    return unknownResult();
  }
  return finalize({
    kind: SessionFormatKind.GENERIC_CHAT_JSON,
    parser_agent: "cline",
    version: "chat-json-v1",
    signature,
    confidence: 0.8,
    details: { message_count: messages.length },
  });
}

function probeGenericMarkdown(stripped, pathHint) {
  if (stripped.startsWith("{") || stripped.startsWith("[")) return unknownResult();
  const head = stripped.slice(0, 2000).toLowerCase();
  const name = (pathHint.name || "").toLowerCase();
  const markers = [
    stripped.startsWith("#"),
    head.includes("## objective"),
    head.includes("## context"),
    name.includes("handoff"),
  ];
  if (!markers.some(Boolean)) return unknownResult();
  return finalize({
    kind: SessionFormatKind.GENERIC_MARKDOWN,
    parser_agent: "cline",
    version: "markdown-v1",
    signature: "markdown_handoff",
    confidence: markers[0] ? 0.75 : 0.6,
    details: {},
  });
}

/**
 * @param {{ name?: string, suffix?: string }} pathHint — filename hints (e.g. from File.name)
 * @param {string} raw — file contents
 */
export function detectSessionFormat(pathHint, raw) {
  const stripped = (raw ?? "").trim();
  if (!stripped) {
    return finalize({
      kind: SessionFormatKind.UNKNOWN,
      parser_agent: "",
      version: null,
      signature: "empty",
      confidence: 0,
      details: {},
    });
  }

  const oc = probeOpencode(stripped);
  if (oc.recognized) return oc;

  const cx = probeCodex(pathHint, stripped);
  if (cx.recognized) return cx;

  const chat = probeGenericChatJson(stripped);
  if (chat.recognized) return chat;

  const md = probeGenericMarkdown(stripped, pathHint);
  if (md.recognized) return md;

  return finalize({
    kind: SessionFormatKind.UNKNOWN,
    parser_agent: "",
    version: null,
    signature: "no_matching_structure",
    confidence: 0,
    details: { path_suffix: pathHint.suffix || "" },
  });
}

export function pathHintFromName(fileName) {
  const name = fileName || "input.txt";
  const dot = name.lastIndexOf(".");
  const suffix = dot >= 0 ? name.slice(dot) : "";
  return { name, suffix };
}

export const NOT_RECOGNIZED_MESSAGE =
  "This format is not recognized.";

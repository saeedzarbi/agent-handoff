import {
  detectSessionFormat,
  pathHintFromName,
  NOT_RECOGNIZED_MESSAGE,
} from "./detection.js";

const SAMPLES = [
  { id: "opencode_min.json", label: "OpenCode export (opencode_min.json)" },
  { id: "codex_min.jsonl", label: "Codex rollout (codex_min.jsonl)" },
  { id: "handoff.md", label: "Markdown handoff (handoff.md)" },
  { id: "chat_min.json", label: "Chat JSON (chat_min.json)" },
  { id: "unknown.json", label: "Unknown JSON (unknown.json)" },
  { id: "empty.txt", label: "Empty file (empty.txt)" },
];

const sampleSelect = document.getElementById("sample-select");
const loadSampleBtn = document.getElementById("load-sample");
const fileInput = document.getElementById("file-input");
const pasteArea = document.getElementById("paste-area");
const detectBtn = document.getElementById("detect-btn");
const clearBtn = document.getElementById("clear-btn");
const resultPanel = document.getElementById("result-panel");
const resultJson = document.getElementById("result-json");

function initSamples() {
  for (const s of SAMPLES) {
    const opt = document.createElement("option");
    opt.value = s.id;
    opt.textContent = s.label;
    sampleSelect.appendChild(opt);
  }
}

async function loadFixture(fileName) {
  const res = await fetch(`fixtures/${fileName}`);
  if (!res.ok) throw new Error(`Could not load fixture: ${fileName}`);
  return res.text();
}

function renderResult(detection) {
  resultPanel.classList.remove("hidden", "result--ok", "result--warn");
  if (detection.recognized) {
    resultPanel.classList.add("result--ok");
  } else {
    resultPanel.classList.add("result--warn");
  }

  const rows = [
    ["Format", detection.kind],
    ["Parser", detection.parser_agent || "—"],
    ["Version", detection.version ?? "—"],
    ["Signature", detection.signature || "—"],
    ["Confidence", detection.confidence.toFixed(2)],
  ];

  if (!detection.recognized) {
    rows.push(["Message", NOT_RECOGNIZED_MESSAGE]);
  }

  resultPanel.innerHTML = rows
    .map(
      ([label, value]) =>
        `<div class="result-row"><span class="result-label">${label}</span><span class="result-value">${escapeHtml(String(value))}</span></div>`,
    )
    .join("");

  resultJson.textContent = JSON.stringify(detection, null, 2);
}

function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function getActiveFileName() {
  if (fileInput.files?.length) return fileInput.files[0].name;
  const sample = sampleSelect.value;
  if (sample) return sample;
  return "pasted-input.txt";
}

function runDetection(raw, fileName) {
  const hint = pathHintFromName(fileName);
  const detection = detectSessionFormat(hint, raw);
  renderResult(detection);
}

async function onLoadSample() {
  const name = sampleSelect.value;
  if (!name) return;
  const text = await loadFixture(name);
  pasteArea.value = text;
  fileInput.value = "";
  runDetection(text, name);
}

function onFileChange() {
  const file = fileInput.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    pasteArea.value = reader.result;
    runDetection(String(reader.result), file.name);
  };
  reader.readAsText(file);
}

function onDetectClick() {
  runDetection(pasteArea.value, getActiveFileName());
}

function onClear() {
  pasteArea.value = "";
  fileInput.value = "";
  sampleSelect.selectedIndex = 0;
  resultPanel.innerHTML = '<p class="muted">Run detection to see format, parser, and signature.</p>';
  resultPanel.classList.remove("result--ok", "result--warn");
  resultJson.textContent = "";
}

initSamples();
loadSampleBtn.addEventListener("click", () => onLoadSample().catch(console.error));
fileInput.addEventListener("change", onFileChange);
detectBtn.addEventListener("click", onDetectClick);
clearBtn.addEventListener("click", onClear);

// Pre-load first sample on visit
onLoadSample().catch(console.error);

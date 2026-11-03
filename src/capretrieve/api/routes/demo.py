"""
api/routes/demo.py — GET /demo: a browser page for demoing the router.

Type a question (or click an example), hit Execute, and the page shows
what the analyzer understood, which sources were selected or blocked and
why, the evidence retrieved, and the final answer — all from one call to
POST /query.

Unlike GET /trace/view, the page itself spends nothing: it is static
until the user submits. The submit is a JSON POST, which another site
cannot send cross-origin without a CORS preflight this app never
approves, so no token is needed.

The script is served from /demo.js rather than inlined so the CSP can
forbid inline scripts, and it builds the results with textContent only,
so query text, evidence and answers are never parsed as HTML.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

router = APIRouter()

DEMO_CSP = (
    "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; "
    "connect-src 'self'"
)

DEMO_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CapRetrieve — Demo</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 980px;
         margin: 2rem auto; padding: 0 1rem; color: #1f2328; }
  h1 { font-size: 1.5rem; margin-bottom: 0.2rem; }
  .sub { color: #59636e; margin-top: 0; }
  textarea { width: 100%; box-sizing: border-box; font: inherit; font-size: 1rem;
             padding: 0.7rem; border: 1px solid #d1d9e0; border-radius: 6px; resize: vertical; }
  .row { display: flex; gap: 0.6rem; align-items: center; margin-top: 0.6rem; }
  button { font: inherit; cursor: pointer; border-radius: 6px; }
  #run { background: #1f883d; color: #fff; border: 0; padding: 0.55rem 1.4rem; font-weight: 600; }
  #run:disabled { background: #8c959f; cursor: wait; }
  #status { color: #59636e; }
  .examples { margin-top: 0.9rem; display: flex; flex-wrap: wrap; gap: 0.4rem; }
  .examples button { background: #f6f8fa; border: 1px solid #d1d9e0; padding: 0.3rem 0.7rem;
                     font-size: 0.85rem; }
  .examples button:hover { background: #eef1f4; }
  h2 { font-size: 1.1rem; border-bottom: 1px solid #d1d9e0; padding-bottom: 0.3rem; margin-top: 2rem; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 0.45rem 0.6rem; border-bottom: 1px solid #eaeef2;
           font-size: 0.9rem; vertical-align: top; }
  th { background: #f6f8fa; }
  .chip { display: inline-block; padding: 0.1rem 0.55rem; border-radius: 999px; font-size: 0.8rem;
          font-weight: 600; }
  .selected { background: #dafbe1; color: #1a7f37; }
  .blocked { background: #ffebe9; color: #cf222e; }
  .skipped { background: #fff8c5; color: #9a6700; }
  .answer { background: #f6f8fa; padding: 1rem; border-radius: 6px; white-space: pre-wrap;
            line-height: 1.5; }
  .error { background: #ffebe9; color: #cf222e; padding: 0.8rem; border-radius: 6px; white-space: pre-wrap; }
  .muted { color: #59636e; font-size: 0.85rem; }
  .question { font-size: 1.05rem; font-weight: 600; }
  details summary { cursor: pointer; color: #0969da; }
  .snippet { white-space: pre-wrap; }
</style>
</head>
<body>
  <h1>CapRetrieve</h1>
  <p class="sub">Ask a question and see which sources the router picks, which it blocks, and why.</p>

  <form id="ask">
    <textarea id="q" rows="3" placeholder="Type a question…" required></textarea>
    <div class="row">
      <button id="run" type="submit">Execute</button>
      <span id="status"></span>
    </div>
  </form>

  <div class="examples">
    <button type="button" data-q="What other notes link to my project retrospective, and what did those say?">Linked notes</button>
    <button type="button" data-q="What does the literature say about intermittent fasting and energy levels?">Literature lookup</button>
    <button type="button" data-q="My HbA1c came back at 7.2 last week. What are the current treatment guidelines for someone at that level?">Health data stays local</button>
    <button type="button" data-q="We agreed 40 million for Project Falcon. Has anything about the acquisition leaked in the press yet?">Confidential deal</button>
    <button type="button" data-q="What did I conclude about my standing desk and back pain?">My own conclusion</button>
    <button type="button" data-q="Has the European Commission published any updates to the AI Act's general-purpose AI code of practice this month?">Needs live web</button>
  </div>

  <div id="result"></div>

  <script src="/demo.js"></script>
</body>
</html>
"""

DEMO_JS = r"""
"use strict";

const SOURCE_NAMES = {
  obsidian: "Obsidian notes (personal vault)",
  chroma: "Document corpus (Chroma)",
  web_search: "Web search (Tavily)",
};

const REQUIREMENT_LABELS = {
  paradigm_hint: "Kind of search",
  relational: "Follows links between notes",
  needs_freshness: "Needs fresh information",
  privacy_sensitivity: "Privacy sensitivity",
  expects_personal_knowledge: "About the user's own notes",
  seed_entity: "Starting note",
};

const form = document.getElementById("ask");
const input = document.getElementById("q");
const runButton = document.getElementById("run");
const statusLine = document.getElementById("status");
const result = document.getElementById("result");

function el(tag, props, children) {
  const node = document.createElement(tag);
  if (props) {
    if (props.className) node.className = props.className;
    if (props.text !== undefined && props.text !== null) node.textContent = String(props.text);
    if (props.title) node.title = props.title;
  }
  for (const child of children || []) node.appendChild(child);
  return node;
}

function table(headers, rows) {
  const head = el("tr", null, headers.map((h) => el("th", { text: h })));
  return el("table", null, [head, ...rows]);
}

function sourceName(id) {
  return SOURCE_NAMES[id] ? SOURCE_NAMES[id] + " — " + id : id;
}

function formatValue(value) {
  if (value === null || value === undefined) return "—";
  if (value === true) return "yes";
  if (value === false) return "no";
  return String(value);
}

function shortUri(uri) {
  if (!uri) return "—";
  const parts = uri.split("/");
  return /^https?:/.test(uri) ? uri : parts[parts.length - 1];
}

function renderRequirements(requirements) {
  const rows = Object.keys(REQUIREMENT_LABELS).map((key) =>
    el("tr", null, [
      el("td", { text: REQUIREMENT_LABELS[key] }),
      el("td", { text: formatValue(requirements[key]) }),
    ])
  );
  return [el("h2", { text: "1. What the analyzer understood" }), table(["Signal", "Value"], rows)];
}

function renderDecisions(plan) {
  const selected = new Set(plan.steps.map((s) => s.connector_id));
  const rows = plan.decisions.map((d) => {
    let chip;
    let reason = "";
    if (selected.has(d.connector_id)) {
      chip = el("span", { className: "chip selected", text: "Selected" });
    } else if (d.admitted) {
      chip = el("span", { className: "chip skipped", text: "Not selected" });
      reason = "Allowed, but scored below the selection cut-off";
    } else {
      chip = el("span", { className: "chip blocked", text: "Blocked" });
      const r = d.exclusion_reason || {};
      reason = (r.constraint ? r.constraint + ": " : "") + (r.detail || "");
    }
    return el("tr", null, [
      el("td", { text: sourceName(d.connector_id) }),
      el("td", null, [chip]),
      el("td", { text: d.score === null || d.score === undefined ? "—" : d.score.toFixed(2) }),
      el("td", { text: reason }),
    ]);
  });
  return [el("h2", { text: "2. Source decisions" }), table(["Source", "Decision", "Score", "Reason"], rows)];
}

function renderAnswer(answer) {
  return [el("h2", { text: "3. Answer" }), el("div", { className: "answer", text: answer || "(empty)" })];
}

function renderEvidence(evidence) {
  if (!evidence.length) {
    return [el("h2", { text: "4. Evidence used" }), el("p", { className: "muted", text: "No evidence was retrieved." })];
  }
  const rows = evidence.map((e, i) => {
    const content = e.content || "";
    const snippet = content.length > 220
      ? el("details", null, [
          el("summary", { text: content.slice(0, 220).replace(/\s+/g, " ") + "…" }),
          el("div", { className: "snippet", text: content }),
        ])
      : el("div", { className: "snippet", text: content });
    return el("tr", null, [
      el("td", { text: String(i + 1) }),
      el("td", { text: e.source_id }),
      el("td", { text: typeof e.score === "number" ? e.score.toFixed(2) : "—" }),
      el("td", { text: shortUri(e.uri), title: e.uri || "" }),
      el("td", null, [snippet]),
    ]);
  });
  return [el("h2", { text: "4. Evidence used" }), table(["#", "Source", "Score", "Item", "Content"], rows)];
}

function renderExecution(execution) {
  const rows = execution.map((r) =>
    el("tr", null, [
      el("td", { text: sourceName(r.connector_id) }),
      el("td", { text: String(r.evidence_count) }),
      el("td", { text: r.error || "—" }),
    ])
  );
  return [el("h2", { text: "5. Execution" }), table(["Source", "Results returned", "Error"], rows)];
}

function render(question, data, seconds) {
  const trace = data.plan_trace;
  const nodes = [
    el("h2", { text: "Question" }),
    el("p", { className: "question", text: question }),
    el("p", { className: "muted", text: "Completed in " + seconds + "s" }),
    ...renderRequirements(trace.requirements),
    ...renderDecisions(trace.execution_plan),
    ...renderAnswer(data.answer),
    ...renderEvidence(data.evidence),
    ...renderExecution(trace.execution),
  ];
  result.replaceChildren(...nodes);
}

function showError(message) {
  result.replaceChildren(el("h2", { text: "Error" }), el("div", { className: "error", text: message }));
}

async function run(question) {
  runButton.disabled = true;
  result.replaceChildren();
  const started = Date.now();
  const tick = () => {
    statusLine.textContent = "Running… " + Math.round((Date.now() - started) / 1000) + "s";
  };
  tick();
  const timer = setInterval(tick, 1000);
  try {
    const resp = await fetch("/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: question, top_k: 5 }),
    });
    const seconds = ((Date.now() - started) / 1000).toFixed(1);
    if (!resp.ok) {
      const body = await resp.text();
      showError("The server returned " + resp.status + ".\n\n" + body.slice(0, 2000));
      statusLine.textContent = "";
      return;
    }
    render(question, await resp.json(), seconds);
    statusLine.textContent = "";
  } catch (err) {
    showError("Could not reach the server: " + err);
    statusLine.textContent = "";
  } finally {
    clearInterval(timer);
    runButton.disabled = false;
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (question) run(question);
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) form.requestSubmit();
});

for (const button of document.querySelectorAll(".examples button")) {
  button.addEventListener("click", () => {
    input.value = button.dataset.q;
    input.focus();
  });
}
"""


@router.get("/demo", response_class=HTMLResponse)
async def demo_page() -> HTMLResponse:
    return HTMLResponse(content=DEMO_HTML, headers={"Content-Security-Policy": DEMO_CSP})


@router.get("/demo.js")
async def demo_script() -> Response:
    return Response(content=DEMO_JS, media_type="application/javascript")

"""
GET /demo: a browser page with a question box that calls POST /query and
renders the decisions, trace and answer. Uses stub connectors over the
real manifests, so it runs without fixtures/data/.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from capretrieve.api.app import create_app
from capretrieve.api.routes.demo import DEMO_JS
from capretrieve.contracts.health import HealthState, HealthStatus
from capretrieve.contracts.result import Evidence, RetrievalResult
from capretrieve.registry.static import build_registry

CONFIG_DIR = Path(__file__).parents[2] / "configs" / "connectors"


class StubConnector:
    def __init__(self, manifest):
        self._manifest = manifest

    def manifest(self):
        return self._manifest

    async def retrieve(self, req) -> RetrievalResult:
        cid = self._manifest.connector_id
        return RetrievalResult(
            evidence=[
                Evidence(
                    source_id=cid,
                    content=f"{cid} result",
                    score=1.0,
                    uri=f"{cid}://0",
                    retrieved_at=datetime.now(timezone.utc),
                )
            ]
        )

    async def health(self) -> HealthStatus:
        return HealthStatus(state=HealthState.OK)


class FakeLLMClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def complete(self, messages: list[dict], **kwargs) -> str:
        self.calls += 1
        return self.response


def _client():
    registry = build_registry(CONFIG_DIR)
    for manifest in registry.manifests().values():
        registry.register(StubConnector(manifest))
    analyzer = FakeLLMClient(
        json.dumps(
            {
                "paradigm_hint": "dense_semantic",
                "relational": False,
                "needs_freshness": "any",
                "privacy_sensitivity": "none",
                "expects_personal_knowledge": False,
                "seed_entity": None,
            }
        )
    )
    app = create_app(registry, analyzer, FakeLLMClient("answer"))
    return TestClient(app), analyzer


def test_demo_page_serves_a_question_form_without_calling_the_llm():
    client, analyzer = _client()

    resp = client.get("/demo")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "<textarea" in resp.text
    assert 'src="/demo.js"' in resp.text
    assert analyzer.calls == 0


def test_demo_page_allows_only_its_own_script():
    client, _ = _client()

    csp = client.get("/demo").headers["content-security-policy"]

    assert "default-src 'none'" in csp
    assert "script-src 'self'" in csp
    assert "connect-src 'self'" in csp
    assert "unsafe-inline" not in csp.split("script-src", 1)[1].split(";")[0]


def test_demo_script_is_served_and_posts_to_query():
    client, _ = _client()

    resp = client.get("/demo.js")

    assert resp.status_code == 200
    assert "javascript" in resp.headers["content-type"]
    assert '"/query"' in resp.text


def test_demo_script_never_injects_html():
    """Query text, evidence and answers are rendered as text, not markup."""
    assert "innerHTML" not in DEMO_JS
    assert "outerHTML" not in DEMO_JS
    assert "insertAdjacentHTML" not in DEMO_JS


# A tiny DOM stand-in, so the page's Markdown renderer can run under Node.
_NODE_HARNESS = r"""
class N {
  constructor(tag, text) { this.tagName = tag ? tag.toUpperCase() : null; this._t = text;
                           this.childNodes = []; this.className = ""; this.title = ""; }
  appendChild(c) { this.childNodes.push(c); return c; }
  get lastChild() { return this.childNodes[this.childNodes.length - 1]; }
  set textContent(v) { this.childNodes = [new N(null, String(v))]; }
  get textContent() { return this.tagName ? this.childNodes.map(c => c.textContent).join("") : this._t; }
  out() {
    if (!this.tagName) return this._t;
    const t = this.tagName.toLowerCase();
    return "<" + t + (this.className ? "." + this.className : "") +
           (this.href ? " href=" + this.href : "") + ">" +
           this.childNodes.map(c => c.out()).join("") + "</" + t + ">";
  }
}
global.document = { createElement: t => new N(t), createTextNode: t => new N(null, t),
                    getElementById: () => new N("div"), querySelectorAll: () => [] };
"""


def _render_markdown_with_node(text: str, allowed_urls: list[str] | None = None) -> str:
    import shutil
    import subprocess

    import pytest

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    # Load the script without its DOM wiring, then call renderMarkdown.
    script = DEMO_JS.split("form.addEventListener")[0]
    program = (
        _NODE_HARNESS
        + script
        + "\nprocess.stdout.write(renderMarkdown("
        + json.dumps(text)
        + ", new Set("
        + json.dumps(allowed_urls or [])
        + ")).out());\n"
    )
    done = subprocess.run(
        [node, "-e", program], capture_output=True, text=True, timeout=20
    )
    assert done.returncode == 0, done.stderr
    return done.stdout


def test_answer_markdown_is_rendered_as_formatting():
    text = (
        "Intro with a cite [1: /a/b/corpus/type2_diabetes_hba1c.md].\n\n"
        "**Plan**\n"
        "- **Lifestyle:** exercise [obsidian: /v/Blood Test Results.md]\n"
        "- second\n\n"
        "## Next\n"
        "1. call *the* doctor, see `notes`\n"
    )
    html = _render_markdown_with_node(text)

    assert "**" not in html
    assert "<strong>Plan</strong>" in html
    assert "<ul><li><strong>Lifestyle:</strong> exercise" in html
    assert "<h3>Next</h3>" in html
    assert "<ol><li>call <em>the</em> doctor, see <code>notes</code></li></ol>" in html
    assert '<span.cite>1 · type2_diabetes_hba1c.md</span>' in html
    assert '<span.cite>obsidian · Blood Test Results.md</span>' in html


def test_answer_markdown_leaves_plain_brackets_alone():
    html = _render_markdown_with_node("See [2] and [note] for more.")

    assert "See [2] and [note] for more." in html
    assert "cite" not in html


def test_answer_link_to_retrieved_evidence_is_clickable_and_shows_its_host():
    url = "https://example.org/eu-ai-act"
    html = _render_markdown_with_node(f"See [the update]({url}).", allowed_urls=[url])

    assert f"<a href={url}>the update (example.org)</a>" in html


def test_answer_link_not_in_evidence_is_plain_text_with_full_url():
    """A prompt-injected link must not hide where it goes behind its text."""
    url = "https://attacker.example/c?d=private-note-text"
    html = _render_markdown_with_node(f"See [your notes]({url}).", allowed_urls=[])

    assert "<a" not in html
    assert f"your notes ({url})" in html

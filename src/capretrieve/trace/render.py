"""
trace/render.py — renders a PlanTrace as JSON or as plain, dependency-free
HTML.

The HTML view is deliberately simple string templating (no Jinja, no
frontend framework) — this is a debugging/demo artifact meant to be
readable by a human without reading the code, not a polished UI. All
user-controlled text (query, evidence content, answer) is HTML-escaped.
"""

from __future__ import annotations

import html

from capretrieve.trace.models import PlanTrace


def render_json(trace: PlanTrace) -> str:
    return trace.model_dump_json(indent=2)


def _decision_row(decision) -> str:
    if decision.admitted:
        return (
            f"<tr><td>{html.escape(decision.connector_id)}</td>"
            f"<td class='admitted'>admitted</td>"
            f"<td>{decision.score:.3f}</td>"
            f"<td>—</td></tr>"
        )
    reason = decision.exclusion_reason
    return (
        f"<tr><td>{html.escape(decision.connector_id)}</td>"
        f"<td class='excluded'>excluded</td>"
        f"<td>—</td>"
        f"<td>{html.escape(reason.constraint)}: {html.escape(reason.detail)}</td></tr>"
    )


def _execution_row(record) -> str:
    return (
        f"<tr><td>{html.escape(record.connector_id)}</td>"
        f"<td>{record.evidence_count}</td>"
        f"<td class='excluded'>{html.escape(record.error or '')}</td></tr>"
    )


def _evidence_row(evidence) -> str:
    uri = evidence.uri if evidence.uri is not None else "(no uri)"
    snippet = evidence.content[:200]
    return (
        f"<tr><td>{html.escape(evidence.source_id)}</td>"
        f"<td>{evidence.score:.3f}</td>"
        f"<td>{html.escape(uri)}</td>"
        f"<td>{html.escape(snippet)}</td></tr>"
    )


def render_html(trace: PlanTrace) -> str:
    """Render a full, self-contained HTML page for one PlanTrace."""
    decision_rows = "\n".join(_decision_row(d) for d in trace.execution_plan.decisions)
    execution_rows = "\n".join(_execution_row(r) for r in trace.execution)
    evidence_rows = "\n".join(_evidence_row(e) for e in trace.fused_evidence)
    selected = ", ".join(trace.execution_plan.selected_connector_ids) or "(none)"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>CapRetrieve — Plan Trace</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; color: #222; }}
  h2 {{ border-bottom: 1px solid #ddd; padding-bottom: 0.3rem; margin-top: 2rem; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 0.5rem; }}
  th, td {{ text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #eee; font-size: 0.9rem; }}
  th {{ background: #fafafa; }}
  .admitted {{ color: #1a7f37; }}
  .excluded {{ color: #cf222e; }}
  .query {{ font-size: 1.1rem; font-weight: 600; }}
  .answer {{ background: #f6f8fa; padding: 1rem; border-radius: 6px; white-space: pre-wrap; }}
</style>
</head>
<body>
  <p class="query">Query: {html.escape(trace.query)}</p>

  <h2>Requirements</h2>
  <pre>{html.escape(trace.requirements.model_dump_json(indent=2))}</pre>

  <h2>Candidates &amp; Selection</h2>
  <table>
    <tr><th>Connector</th><th>Status</th><th>Score</th><th>Reason (if excluded)</th></tr>
    {decision_rows}
  </table>
  <p><strong>Selected:</strong> {html.escape(selected)}</p>

  <h2>Execution</h2>
  <table>
    <tr><th>Connector</th><th>Evidence Count</th><th>Error</th></tr>
    {execution_rows}
  </table>

  <h2>Fused Evidence</h2>
  <table>
    <tr><th>Source</th><th>Score</th><th>URI</th><th>Snippet</th></tr>
    {evidence_rows}
  </table>

  <h2>Answer</h2>
  <div class="answer">{html.escape(trace.answer)}</div>
</body>
</html>
"""
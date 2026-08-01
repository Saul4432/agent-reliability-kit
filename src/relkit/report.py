"""Self-contained HTML report for a suite run (no external assets)."""

from __future__ import annotations

import html
from pathlib import Path

from relkit.models import CaseKind, SuiteResult

_CSS = """
body{font-family:system-ui,sans-serif;margin:2rem auto;max-width:960px;
  color:#1c2333;background:#f7f8fb}
h1{font-size:1.4rem} .muted{color:#667085}
table{border-collapse:collapse;width:100%;margin:1rem 0;background:#fff}
th,td{padding:.5rem .7rem;border-bottom:1px solid #e4e7ec;text-align:left;
  font-size:.9rem;vertical-align:top}
.bar{background:#e4e7ec;border-radius:4px;height:10px;width:160px;display:inline-block;vertical-align:middle}
.bar>i{display:block;height:10px;border-radius:4px;background:#2e6bd6}
.fail .bar>i{background:#d64545}
.badge{border-radius:10px;padding:.1rem .55rem;font-size:.75rem;font-weight:600}
.ok{background:#e6f4ea;color:#137333}.ko{background:#fce8e6;color:#a50e0e}
.planted{background:#fff4e5;color:#8a5300}
pre{white-space:pre-wrap;font-size:.8rem;margin:0;color:#475467}
"""


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_html(result: SuiteResult) -> str:
    """Render the suite result as a single self-contained HTML document."""
    rows = []
    for s in result.summaries:
        ok = s.mean_score >= s.threshold
        rows.append(
            f"<tr class='{'' if ok else 'fail'}'><td>{html.escape(s.metric)}</td>"
            f"<td><span class='bar'><i style='width:{s.mean_score * 100:.0f}%'></i></span> "
            f"{s.mean_score:.3f}</td><td>{s.threshold:.2f}</td><td>{_pct(s.pass_rate)}</td>"
            f"<td><span class='badge {'ok' if ok else 'ko'}'>"
            f"{'PASS' if ok else 'FAIL'}</span></td></tr>"
        )

    case_rows = []
    for c in result.cases:
        kind_badge = (
            "<span class='badge planted'>planted</span>"
            if c.kind is CaseKind.planted_failure
            else ""
        )
        detail = "; ".join(f"{m.metric}={m.score:.2f}" for m in c.metrics)
        case_rows.append(
            f"<tr><td>{html.escape(c.case_id)} {kind_badge}</td>"
            f"<td><span class='badge {'ok' if c.passed else 'ko'}'>"
            f"{'pass' if c.passed else 'fail'}</span></td>"
            f"<td>{c.latency_ms:.0f}ms</td>"
            f"<td><pre>{html.escape(c.output[:300])}</pre>"
            f"<span class='muted'>{detail}</span></td></tr>"
        )

    return f"""<!doctype html><html><head><meta charset='utf-8'>
<title>relkit — {html.escape(result.suite_name)}</title><style>{_CSS}</style></head><body>
<h1>Agent Reliability Report — {html.escape(result.suite_name)}</h1>
<p class='muted'>{len(result.cases)} cases · suite pass rate {_pct(result.pass_rate)}
 · eval cost ${result.total_cost_usd:.4f}</p>
<h2>Metrics</h2>
<table><tr><th>Metric</th><th>Mean score</th><th>Threshold</th>
<th>Case pass rate</th><th>Gate</th></tr>
{"".join(rows)}</table>
<h2>Cases</h2>
<table><tr><th>Case</th><th>Result</th><th>Latency</th><th>Output & scores</th></tr>
{"".join(case_rows)}</table>
</body></html>"""


def write_report(result: SuiteResult, path: str | Path) -> Path:
    out = Path(path)
    out.write_text(render_html(result), "utf-8")
    return out

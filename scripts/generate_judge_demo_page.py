#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

METRIC_RE = re.compile(r"^- ([^:]+): (.+) \[([A-Z]+)\] \((.*)\)$")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def parse_kv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in read_text(path).splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def checklist_progress(path: Path) -> tuple[int, int]:
    done = 0
    total = 0
    for line in read_text(path).splitlines():
        if line.startswith("- [x] ") or line.startswith("- [ ] "):
            total += 1
            if line.startswith("- [x] "):
                done += 1
    return done, total


def parse_scorecard_metrics(path: Path) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for line in read_text(path).splitlines():
        m = METRIC_RE.match(line.strip())
        if m:
            rows.append((m.group(1), m.group(2), m.group(3)))
    return rows


def status_chip(status: str) -> str:
    if status == "PASS":
        return '<span class="chip pass">PASS</span>'
    if status == "WARN":
        return '<span class="chip warn">WARN</span>'
    return '<span class="chip unknown">UNKNOWN</span>'


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate polished judge demo page from artifacts."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--out", default="docs/lessons/judge-demo.html", help="Output HTML path")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    out = Path(args.out).resolve() if Path(args.out).is_absolute() else (repo_root / args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    checklist = repo_root / "artifacts/tars/judge_demo_checklist.md"
    scorecard = repo_root / "artifacts/devloop/profit_readiness_scorecard.md"
    smoke = parse_kv(repo_root / "artifacts/tars/smoke_metrics.txt")
    exec_daily = read_json(repo_root / "artifacts/tars/execution_quality_daily.json")
    loop_status = parse_kv(repo_root / "artifacts/devloop/status.txt")

    done, total = checklist_progress(checklist)
    metrics = parse_scorecard_metrics(scorecard)
    loop_cycle = loop_status.get("cycle", "n/a")
    loop_profile = loop_status.get("profile", "n/a")
    latency = smoke.get("latency_ms", "n/a")
    est_cost = smoke.get("estimated_total_cost_usd", "n/a")

    exec_success = exec_daily.get("success_rate", "n/a")
    exec_actionable = exec_daily.get("actionable_rate", "n/a")
    exec_runs = exec_daily.get("run_count", "n/a")
    exec_p95 = exec_daily.get("p95_latency_ms", "n/a")
    generated_at = exec_daily.get("generated_at_utc", "n/a")

    metric_rows = (
        "\n".join(
            f"<tr><td>{name}</td><td>{value}</td><td>{status_chip(status)}</td></tr>"
            for name, value, status in metrics[:12]
        )
        or '<tr><td colspan="3">No scorecard metrics found yet.</td></tr>'
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Judge Demo Evidence</title>
  <style>
    :root {{
      --bg: #061321;
      --panel: #10263e;
      --panel2: #163557;
      --text: #eef6ff;
      --muted: #b7cbe4;
      --line: #2b4f78;
      --accent: #ff8f42;
      --pass: #2ecc71;
      --warn: #f4c542;
      --unk: #95a5a6;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: radial-gradient(circle at 20% 0%, #1d3d66 0%, var(--bg) 50%);
      color: var(--text);
      font-family: "Avenir Next", "Segoe UI", sans-serif;
    }}
    .wrap {{ max-width: 1120px; margin: 0 auto; padding: 28px 18px 42px; }}
    .hero {{
      border: 1px solid var(--line);
      background: linear-gradient(135deg, var(--panel), var(--panel2));
      border-radius: 16px;
      padding: 22px;
    }}
    h1 {{ margin: 0 0 8px; font-size: clamp(1.6rem, 3vw, 2.2rem); }}
    p {{ margin: 0; color: var(--muted); line-height: 1.5; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 14px;
      margin-top: 14px;
    }}
    .card {{
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 14px;
      padding: 14px;
    }}
    .span4 {{ grid-column: span 4; }}
    .span6 {{ grid-column: span 6; }}
    .span8 {{ grid-column: span 8; }}
    .span12 {{ grid-column: span 12; }}
    .k {{
      color: var(--muted);
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }}
    .v {{ font-size: 1.45rem; font-weight: 700; margin-top: 4px; }}
    .table {{ width: 100%; border-collapse: collapse; }}
    .table td {{
      border-bottom: 1px solid rgba(255,255,255,0.08);
      padding: 10px 6px;
      vertical-align: top;
      font-size: 0.95rem;
    }}
    .chip {{
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 0.74rem;
      font-weight: 700;
      display: inline-block;
    }}
    .pass {{ background: var(--pass); color: #092414; }}
    .warn {{ background: var(--warn); color: #312500; }}
    .unknown {{ background: var(--unk); color: #102026; }}
    .flow {{
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 10px;
    }}
    .node {{
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
      border-radius: 10px;
      min-height: 60px;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 8px;
      font-size: 0.88rem;
    }}
    .arr {{ text-align: center; color: var(--accent); font-weight: 800; }}
    .links a {{ color: #9ed0ff; text-decoration: none; }}
    .links li {{ margin: 6px 0; color: var(--muted); }}
    @media (max-width: 920px) {{
      .span4, .span6, .span8 {{ grid-column: span 12; }}
      .flow {{ grid-template-columns: 1fr; }}
      .arr {{ transform: rotate(90deg); }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>Judge Demo Evidence Hub</h1>
      <p>This page translates complex AI product behavior into clear proof.
      Audience mode: simple enough for non-technical viewers, concrete enough for technical judges.</p>
    </section>

    <section class="grid">
      <article class="card span4"><div class="k">Checklist Progress</div><div class="v">{done}/{total}</div></article>
      <article class="card span4"><div class="k">System Status</div><div class="v">{loop_cycle} / {loop_profile}</div></article>
      <article class="card span4"><div class="k">Smoke Latency / Cost</div><div class="v">{latency} ms / ${est_cost}</div></article>

      <article class="card span6">
        <div class="k">Execution Quality Daily</div>
        <table class="table">
          <tr><td>Runs</td><td>{exec_runs}</td></tr>
          <tr><td>Success Rate</td><td>{exec_success}%</td></tr>
          <tr><td>Actionable Rate</td><td>{exec_actionable}%</td></tr>
          <tr><td>P95 Latency</td><td>{exec_p95} ms</td></tr>
          <tr><td>Generated</td><td>{generated_at}</td></tr>
        </table>
      </article>

      <article class="card span6">
        <div class="k">Product Proof Flow</div>
        <div class="flow" style="margin-top:10px">
          <div class="node">1. Collect Signals</div><div class="arr">-></div><div class="node">2. Generate Decision</div><div class="arr">-></div><div class="node">3. Validate Output</div>
        </div>
        <div class="flow" style="margin-top:10px">
          <div class="node">4. KPI + Scorecard</div><div class="arr">-></div><div class="node">5. Update Knowledge</div><div class="arr">-></div><div class="node">6. Improve Quality</div>
        </div>
      </article>

      <article class="card span8">
        <div class="k">Readiness Metrics</div>
        <table class="table">{metric_rows}</table>
      </article>

      <article class="card span4 links">
        <div class="k">Evidence Files</div>
        <ul>
          <li><a href="../../artifacts/tars/submission_summary.md">submission_summary.md</a></li>
          <li><a href="../../artifacts/tars/judge_demo_checklist.md">judge_demo_checklist.md</a></li>
          <li><a href="../../artifacts/tars/trade_opinion_smoke.json">trade_opinion_smoke.json</a></li>
          <li><a href="../../artifacts/tars/execution_quality_daily.json">execution_quality_daily.json</a></li>
          <li><a href="../../artifacts/devloop/profit_readiness_scorecard.md">profit_readiness_scorecard.md</a></li>
          <li><a href="../../docs/_reports/hackathon-system-explainer.md">system explainer</a></li>
        </ul>
      </article>
    </section>
  </div>
</body>
</html>
"""

    out.write_text(html, encoding="utf-8")
    print(f"ok: judge demo page generated -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

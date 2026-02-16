#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def safe_read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def parse_kv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = int(round((p / 100.0) * (len(ordered) - 1)))
    idx = max(0, min(idx, len(ordered) - 1))
    return ordered[idx]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def to_int(value: Any) -> int | None:
    try:
        return int(float(value))
    except Exception:
        return None


def event_from_artifacts(artifact_dir: Path) -> dict[str, Any]:
    metrics = parse_kv(artifact_dir / "smoke_metrics.txt")
    trade_opinion = safe_read_json(artifact_dir / "trade_opinion_smoke.json")

    timestamp = metrics.get("timestamp_utc") or utc_now_iso()
    event = {
        "timestamp_utc": timestamp,
        "date_utc": timestamp[:10],
        "latency_ms": to_int(metrics.get("latency_ms")),
        "estimated_total_cost_usd": to_float(metrics.get("estimated_total_cost_usd")),
        "prompt_tokens": to_int(metrics.get("prompt_tokens")),
        "completion_tokens": to_int(metrics.get("completion_tokens")),
        "total_tokens": to_int(metrics.get("total_tokens")),
        "actionable": bool(trade_opinion.get("actionable")),
        "success": bool(trade_opinion.get("ok")) and bool(trade_opinion.get("actionable")),
        "fallback_probe_ok": bool(trade_opinion.get("fallback_probe_ok")),
        "chosen_model": str(trade_opinion.get("chosen_model") or ""),
        "attempts_count": len(trade_opinion.get("attempts") or []),
    }
    return event


def append_event(log_path: Path, event: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=True) + "\n")


def load_events_for_date(log_path: Path, date_utc: str) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            row = json.loads(line)
        except Exception:
            continue
        if not isinstance(row, dict):
            continue
        if str(row.get("date_utc")) == date_utc:
            events.append(row)
    return events


def aggregate(events: list[dict[str, Any]], date_utc: str) -> dict[str, Any]:
    latencies = [float(v) for v in (e.get("latency_ms") for e in events) if isinstance(v, (int, float))]
    costs = [
        float(v)
        for v in (e.get("estimated_total_cost_usd") for e in events)
        if isinstance(v, (int, float))
    ]
    total = len(events)
    success_count = sum(1 for e in events if e.get("success") is True)
    actionable_count = sum(1 for e in events if e.get("actionable") is True)
    fallback_ok_count = sum(1 for e in events if e.get("fallback_probe_ok") is True)
    models: dict[str, int] = {}
    for e in events:
        model = str(e.get("chosen_model") or "").strip()
        if not model:
            continue
        models[model] = models.get(model, 0) + 1

    return {
        "date_utc": date_utc,
        "generated_at_utc": utc_now_iso(),
        "run_count": total,
        "success_count": success_count,
        "success_rate": round((success_count / total) * 100.0, 2) if total else 0.0,
        "actionable_count": actionable_count,
        "actionable_rate": round((actionable_count / total) * 100.0, 2) if total else 0.0,
        "fallback_probe_ok_count": fallback_ok_count,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "p95_latency_ms": round(percentile(latencies, 95.0), 2) if latencies else None,
        "total_estimated_cost_usd": round(sum(costs), 8) if costs else None,
        "avg_estimated_cost_usd": round(sum(costs) / len(costs), 8) if costs else None,
        "model_usage": models,
    }


def write_markdown(path: Path, agg: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# TARS Execution Quality Daily")
    lines.append("")
    lines.append(f"- Date (UTC): `{agg['date_utc']}`")
    lines.append(f"- Generated: `{agg['generated_at_utc']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Runs: `{agg['run_count']}`")
    lines.append(f"- Success Rate: `{agg['success_rate']}%`")
    lines.append(f"- Actionable Rate: `{agg['actionable_rate']}%`")
    lines.append(f"- Fallback Probe OK Count: `{agg['fallback_probe_ok_count']}`")
    lines.append(f"- Avg Latency: `{agg['avg_latency_ms']} ms`")
    lines.append(f"- P95 Latency: `{agg['p95_latency_ms']} ms`")
    lines.append(f"- Total Estimated Cost: `${agg['total_estimated_cost_usd']}`")
    lines.append(f"- Avg Estimated Cost: `${agg['avg_estimated_cost_usd']}`")
    lines.append("")
    lines.append("## Model Usage")
    if agg["model_usage"]:
        for model, count in sorted(agg["model_usage"].items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- `{model}`: `{count}`")
    else:
        lines.append("- none")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate daily TARS execution quality aggregate.")
    parser.add_argument("--artifact-dir", default="artifacts/tars", help="TARS artifact directory")
    parser.add_argument(
        "--events-log",
        default="artifacts/tars/execution_quality_events.jsonl",
        help="Append-only execution events log",
    )
    parser.add_argument(
        "--out-json",
        default="artifacts/tars/execution_quality_daily.json",
        help="Daily aggregate JSON output",
    )
    parser.add_argument(
        "--out-md",
        default="artifacts/tars/execution_quality_daily.md",
        help="Daily aggregate markdown output",
    )
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir)
    log_path = Path(args.events_log)
    out_json = Path(args.out_json)
    out_md = Path(args.out_md)

    event = event_from_artifacts(artifact_dir)
    append_event(log_path, event)

    date_utc = str(event.get("date_utc"))
    events = load_events_for_date(log_path, date_utc)
    agg = aggregate(events, date_utc=date_utc)

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(agg, indent=2) + "\n", encoding="utf-8")
    write_markdown(out_md, agg)
    print(f"ok: execution quality aggregate -> {out_json}")
    print(f"ok: execution quality report -> {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

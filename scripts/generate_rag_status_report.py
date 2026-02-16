#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def read_kv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def count_lessons(root: Path) -> int:
    if not root.exists():
        return 0
    return len(list(root.rglob("*.md")))


def fmt_mtime(path: Path) -> str:
    if not path.exists():
        return "N/A"
    dt = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def yes_no(v: bool) -> str:
    return "yes" if v else "no"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate RAG refresh status report.")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--out",
        default="artifacts/devloop/rag_status.md",
        help="Output markdown report path",
    )
    parser.add_argument(
        "--refresh-log",
        default="artifacts/devloop/rag_refresh.log",
        help="Path to refresh log",
    )
    parser.add_argument(
        "--status-file",
        default="artifacts/devloop/rag_refresh_status.txt",
        help="Path to step status kv file",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    out = (repo_root / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)
    refresh_log = (
        (repo_root / args.refresh_log).resolve()
        if not Path(args.refresh_log).is_absolute()
        else Path(args.refresh_log)
    )
    status_file = (
        (repo_root / args.status_file).resolve()
        if not Path(args.status_file).is_absolute()
        else Path(args.status_file)
    )
    out.parent.mkdir(parents=True, exist_ok=True)

    rag_knowledge_root = repo_root / "rag_knowledge"
    lessons_root = rag_knowledge_root / "lessons_learned"
    lancedb_root = repo_root / ".claude" / "memory" / "lancedb"
    lancedb_stats = lancedb_root / "index_stats.json"
    query_index = repo_root / "data" / "rag" / "lessons_query.json"
    docs_query_index = repo_root / "docs" / "data" / "rag" / "lessons_query.json"

    stats = read_json(lancedb_stats)
    step_status = read_kv(status_file)
    files_processed = stats.get("files_processed", "N/A")
    chunks_created = stats.get("chunks_created", "N/A")
    errors = stats.get("errors", [])
    last_indexed = stats.get("last_indexed", "N/A")
    if isinstance(errors, list):
        error_count = len(errors)
    else:
        error_count = "N/A"

    reindex_exit = step_status.get("reindex_exit", "N/A")
    query_index_exit = step_status.get("query_index_exit", "N/A")

    total_lessons = count_lessons(lessons_root)
    total_rag_markdown = count_lessons(rag_knowledge_root)

    lines: list[str] = []
    lines.append("# RAG Status Report")
    lines.append("")
    lines.append(f"- Generated (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    lines.append("")
    lines.append("## Coverage")
    lines.append(f"- `rag_knowledge/**/*.md` files: {total_rag_markdown}")
    lines.append(f"- `rag_knowledge/lessons_learned/*.md` files: {total_lessons}")
    lines.append("")
    lines.append("## Index Health")
    lines.append(f"- LanceDB path exists: {yes_no(lancedb_root.exists())}")
    lines.append(f"- LanceDB stats file exists: {yes_no(lancedb_stats.exists())}")
    lines.append(f"- Last indexed (from stats): {last_indexed}")
    lines.append(f"- Files processed (last run): {files_processed}")
    lines.append(f"- Chunks created (last run): {chunks_created}")
    lines.append(f"- Errors (last run): {error_count}")
    lines.append("")
    lines.append("## Refresh Steps")
    lines.append(f"- Reindex exit: {reindex_exit}")
    lines.append(f"- Query index exit: {query_index_exit}")
    lines.append("")
    lines.append("## Query Index Health")
    lines.append(f"- `data/rag/lessons_query.json` exists: {yes_no(query_index.exists())}")
    lines.append(f"- `data/rag/lessons_query.json` mtime: {fmt_mtime(query_index)}")
    lines.append(
        f"- `docs/data/rag/lessons_query.json` exists: {yes_no(docs_query_index.exists())}"
    )
    lines.append(f"- `docs/data/rag/lessons_query.json` mtime: {fmt_mtime(docs_query_index)}")
    lines.append("")
    lines.append("## Refresh Log")
    lines.append(f"- Log file: `{refresh_log}`")
    lines.append(f"- Log mtime: {fmt_mtime(refresh_log)}")
    lines.append(f"- Status file: `{status_file}`")
    lines.append(f"- Status mtime: {fmt_mtime(status_file)}")
    lines.append("")
    lines.append("## Communication Copy")
    overall_ok = reindex_exit == "0" and query_index_exit == "0"
    lines.append(
        f"- RAG refresh overall: {'PASS' if overall_ok else 'PARTIAL/FAIL'} "
        f"(reindex_exit={reindex_exit}, query_index_exit={query_index_exit})."
    )
    lines.append(
        f"- RAG refresh status: indexed `{files_processed}` files into `{chunks_created}` chunks, "
        f"errors=`{error_count}`, last indexed=`{last_indexed}`."
    )
    lines.append(
        f"- Query index freshness: data mtime=`{fmt_mtime(query_index)}`, docs mtime=`{fmt_mtime(docs_query_index)}`."
    )
    lines.append("")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"ok: rag status report -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

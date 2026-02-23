#!/usr/bin/env python3
"""Publish a daily report to Dev.to, LinkedIn, X, and record verification artifacts."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.cross_publish import parse_frontmatter, publish_to_devto, publish_to_linkedin
from scripts.publish_twitter import (
    generate_twitter_post,
    missing_credential_names,
    post_to_twitter,
    resolve_credentials,
)

ET = ZoneInfo("America/New_York")
DEFAULT_SITE_URL = "https://igorganapolsky.github.io/trading"
PAPERBANANA_PAPER_RE = re.compile(r"paperbanana_paper(?:_[^)\s\"']+)?\.svg", re.IGNORECASE)
PAPERBANANA_LIVE_RE = re.compile(r"paperbanana_live(?:_[^)\s\"']+)?\.svg", re.IGNORECASE)


@dataclass
class PlatformResult:
    status: str
    detail: str = ""
    url: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"status": self.status, "detail": self.detail}
        if self.url:
            payload["url"] = self.url
        return payload


def _derive_report_date(report_path: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    match = re.match(r"^(\d{4}-\d{2}-\d{2})-", report_path.name)
    if match:
        return match.group(1)
    return datetime.now(ET).date().isoformat()


def _canonical_url(report_path: Path, frontmatter: dict[str, Any], site_url: str) -> str:
    canonical = str(frontmatter.get("canonical_url") or "").strip()
    if canonical:
        return canonical
    stem = report_path.stem
    return f"{site_url}/reports/{stem}/"


def _title(report_path: Path, frontmatter: dict[str, Any], body: str) -> str:
    fm_title = str(frontmatter.get("title") or "").strip()
    if fm_title:
        return fm_title
    for line in body.splitlines():
        text = line.strip()
        if text.startswith("# "):
            return text[2:].strip()
    return report_path.stem.replace("-", " ").title()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def _write_markdown_report(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    generated_et = result.get("generated_at_et", "")
    report_date = result.get("date", "")
    report_file = result.get("report_path", "")
    canonical_url = result.get("canonical_url", "")
    title = result.get("title", "")
    platforms = result.get("platforms", {})

    lines = [
        "---",
        "layout: post",
        f'title: "Publication Status - {report_date}"',
        f"date: {report_date}",
        "---",
        "",
        f"# Daily Publication Status - {report_date}",
        "",
        f"- Generated (ET): `{generated_et}`",
        f"- Report file: `{report_file}`",
        f"- Canonical URL: {canonical_url}",
        f"- Title: {title}",
        "",
        "| Platform | Status | Details |",
        "|---|---|---|",
    ]

    for name in ("gh_pages", "devto", "linkedin", "x"):
        info = platforms.get(name, {})
        status = str(info.get("status", "unknown"))
        detail = str(info.get("detail", ""))
        url = str(info.get("url", "")) if info.get("url") else ""
        extra = f"{detail} {url}".strip()
        lines.append(f"| {name} | {status} | {extra} |")

    verification = result.get("verification", {})
    if verification:
        lines.extend(
            [
                "",
                "## Verification",
                "",
                "| Check | Status | Details |",
                "|---|---|---|",
            ]
        )
        for check_name, payload in verification.items():
            if not isinstance(payload, dict):
                continue
            status = str(payload.get("status", "unknown"))
            detail = str(payload.get("detail", ""))
            lines.append(f"| {check_name} | {status} | {detail} |")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_agents_markdown_report(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    report_date = str(result.get("date", "unknown"))
    title = str(result.get("title", "Daily Trading Report"))
    canonical_url = str(result.get("canonical_url", ""))
    generated_utc = str(result.get("generated_at_utc", ""))
    platforms = result.get("platforms", {})
    verification = result.get("verification", {})

    lines = [
        "---",
        f'title: "Agent Brief - {report_date}"',
        "---",
        "",
        f"# Agent Brief: {title}",
        "",
        f"- report_date: `{report_date}`",
        f"- generated_at_utc: `{generated_utc}`",
        f"- canonical_url: {canonical_url}",
        "",
        "## Publication Status",
    ]

    for name in ("gh_pages", "devto", "linkedin", "x"):
        info = platforms.get(name, {})
        if not isinstance(info, dict):
            continue
        status = str(info.get("status", "unknown"))
        detail = str(info.get("detail", ""))
        url = str(info.get("url", ""))
        line = f"- {name}: `{status}`"
        if detail:
            line += f" - {detail}"
        if url:
            line += f" ({url})"
        lines.append(line)

    lines.extend(["", "## Content Verification"])
    for check_name, payload in verification.items():
        if not isinstance(payload, dict):
            continue
        status = str(payload.get("status", "unknown"))
        detail = str(payload.get("detail", ""))
        lines.append(f"- {check_name}: `{status}` - {detail}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _paperbanana_verification(markdown: str) -> dict[str, Any]:
    paper = PAPERBANANA_PAPER_RE.search(markdown)
    live = PAPERBANANA_LIVE_RE.search(markdown)
    has_section = "PaperBanana" in markdown
    ok = bool(paper and live and has_section)
    details: list[str] = []
    if not has_section:
        details.append("PaperBanana section heading missing")
    if not paper:
        details.append("paper account diagram reference missing")
    if not live:
        details.append("brokerage account diagram reference missing")
    if ok:
        details.append("report includes paper+brokerage PaperBanana diagram references")
    return {
        "status": "success" if ok else "failed",
        "detail": "; ".join(details),
        "paper_ref": paper.group(0) if paper else "",
        "live_ref": live.group(0) if live else "",
    }


def _verify_live_url(url: str, *, allow_pending: bool = False) -> PlatformResult:
    try:
        response = requests.get(
            url,
            timeout=20,
            allow_redirects=True,
            headers={"User-Agent": "trading-publication-verifier/1.0"},
        )
    except requests.RequestException as exc:
        return PlatformResult("failed", f"Live URL probe failed: {exc.__class__.__name__}")

    if response.status_code == 404 and allow_pending:
        return PlatformResult(
            "pending",
            "Live URL returned HTTP 404 (likely waiting for Pages deploy)",
            url=url,
        )

    if response.status_code >= 400:
        return PlatformResult("failed", f"Live URL probe returned HTTP {response.status_code}", url=url)

    resolved = str(response.url) if response.url else url
    return PlatformResult("success", f"Live URL probe returned HTTP {response.status_code}", url=resolved)


def _verify_devto_diagrams(article_url: str) -> PlatformResult:
    try:
        response = requests.get(
            article_url,
            timeout=20,
            headers={"User-Agent": "trading-publication-verifier/1.0"},
        )
    except requests.RequestException as exc:
        return PlatformResult("failed", f"Dev.to verification failed: {exc.__class__.__name__}", url=article_url)

    if response.status_code >= 400:
        return PlatformResult(
            "failed",
            f"Dev.to verification returned HTTP {response.status_code}",
            url=article_url,
        )

    html = response.text
    has_paper = bool(PAPERBANANA_PAPER_RE.search(html))
    has_live = bool(PAPERBANANA_LIVE_RE.search(html))
    if has_paper and has_live:
        return PlatformResult("success", "Published with PaperBanana diagrams", url=article_url)
    missing = []
    if not has_paper:
        missing.append("paper")
    if not has_live:
        missing.append("brokerage")
    return PlatformResult(
        "failed",
        f"Published but missing PaperBanana diagrams in Dev.to HTML: {', '.join(missing)}",
        url=article_url,
    )


def _load_timeline(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _save_timeline(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


def _upsert_timeline_entry(path: Path, entry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _load_timeline(path)
    entry_id = str(entry.get("id", ""))
    rows = [row for row in rows if str(row.get("id", "")) != entry_id]
    rows.insert(0, entry)
    rows.sort(
        key=lambda row: str(row.get("generated_at_utc", row.get("date", ""))),
        reverse=True,
    )
    rows = rows[:180]
    _save_timeline(path, rows)
    return rows


def _write_beats_page(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        "layout: page",
        'title: "Beats"',
        "---",
        "",
        "# Beats",
        "",
        "One timeline for everything we shipped: reports, posts, and cross-publishing status.",
        "",
    ]
    for row in rows[:90]:
        date = str(row.get("date", "unknown"))
        title = str(row.get("title", "Untitled"))
        canonical_url = str(row.get("canonical_url", ""))
        platforms = row.get("platforms", {})
        badges = ["report"]
        if isinstance(platforms, dict):
            for name in ("gh_pages", "devto", "linkedin", "x"):
                state = str((platforms.get(name, {}) or {}).get("status", ""))
                if state == "success":
                    badges.append(name)
                elif state == "pending":
                    badges.append(f"{name}-pending")
        badge_text = " ".join(f"`{badge}`" for badge in badges)
        line = f"- **{date}** [{title}]({canonical_url}) {badge_text}".rstrip()
        lines.append(line)

        refs = row.get("paperbanana_refs", {})
        if isinstance(refs, dict):
            paper_ref = str(refs.get("paper", ""))
            live_ref = str(refs.get("live", ""))
            if paper_ref and live_ref:
                lines.append(
                    f"  - diagrams: `{paper_ref}` + `{live_ref}`"
                )

        if isinstance(platforms, dict):
            platform_links = []
            for name in ("devto", "linkedin", "x"):
                info = platforms.get(name, {})
                if not isinstance(info, dict):
                    continue
                url = str(info.get("url", ""))
                if url:
                    platform_links.append(f"[{name}]({url})")
            if platform_links:
                lines.append(f"  - cross-posts: {', '.join(platform_links)}")

    lines.extend(["", "_Auto-generated by `scripts/publish_daily_multiplatform.py`._", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def publish_daily_report(
    report_path: Path,
    *,
    report_date: str | None = None,
    site_url: str = DEFAULT_SITE_URL,
    strict: bool = False,
    dry_run: bool = False,
) -> tuple[int, dict[str, Any]]:
    if not report_path.exists():
        result = {
            "date": report_date or datetime.now(ET).date().isoformat(),
            "report_path": str(report_path),
            "generated_at_et": datetime.now(ET).isoformat(),
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "error": "report_missing",
            "platforms": {
                "gh_pages": PlatformResult("failed", "Report file does not exist").as_dict(),
                "devto": PlatformResult("skipped", "No report to publish").as_dict(),
                "linkedin": PlatformResult("skipped", "No report to publish").as_dict(),
                "x": PlatformResult("skipped", "No report to publish").as_dict(),
            },
        }
        return 1, result

    raw = report_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(raw)
    computed_date = _derive_report_date(report_path, report_date)
    title = _title(report_path, frontmatter, body)
    canonical = _canonical_url(report_path, frontmatter, site_url)
    paperbanana_check = _paperbanana_verification(raw)
    tags = frontmatter.get("tags", frontmatter.get("categories", ["ai", "trading", "automation"]))
    if not isinstance(tags, list):
        tags = ["ai", "trading", "automation"]

    platforms: dict[str, dict[str, Any]] = {}

    today_et = datetime.now(ET).date().isoformat()
    platforms["gh_pages"] = _verify_live_url(
        canonical,
        allow_pending=computed_date == today_et,
    ).as_dict()

    devto_key = os.environ.get("DEVTO_API_KEY") or os.environ.get("DEV_TO_API_KEY")
    if not devto_key:
        platforms["devto"] = PlatformResult("skipped", "DEVTO_API_KEY missing").as_dict()
    else:
        try:
            devto_url = publish_to_devto(title, body, tags, canonical)
            if devto_url:
                platforms["devto"] = _verify_devto_diagrams(devto_url).as_dict()
            else:
                platforms["devto"] = PlatformResult("failed", "API publish failed").as_dict()
        except Exception as exc:  # pragma: no cover - defensive
            platforms["devto"] = PlatformResult("failed", f"Exception: {exc}").as_dict()

    linkedin_token = re.sub(r"\s+", "", os.environ.get("LINKEDIN_ACCESS_TOKEN", ""))
    if not linkedin_token:
        platforms["linkedin"] = PlatformResult("skipped", "LINKEDIN_ACCESS_TOKEN missing").as_dict()
    else:
        try:
            linkedin_ok = publish_to_linkedin(title, body, canonical)
            if linkedin_ok:
                platforms["linkedin"] = PlatformResult("success", "Published").as_dict()
            else:
                platforms["linkedin"] = PlatformResult("failed", "API publish failed").as_dict()
        except Exception as exc:  # pragma: no cover - defensive
            platforms["linkedin"] = PlatformResult("failed", f"Exception: {exc}").as_dict()

    x_credentials = resolve_credentials()
    x_missing = missing_credential_names(x_credentials)
    if x_missing:
        platforms["x"] = PlatformResult(
            "skipped", f"Missing credentials: {', '.join(x_missing)}"
        ).as_dict()
    else:
        tweet = generate_twitter_post("positive", title, canonical)
        x_ok = post_to_twitter(tweet, dry_run=dry_run)
        platforms["x"] = (
            PlatformResult("success", "Published")
            if x_ok
            else PlatformResult("failed", "API publish failed")
        ).as_dict()

    result = {
        "date": computed_date,
        "report_path": str(report_path),
        "title": title,
        "canonical_url": canonical,
        "generated_at_et": datetime.now(ET).isoformat(),
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "platforms": platforms,
        "verification": {
            "paperbanana_in_report": {
                "status": paperbanana_check["status"],
                "detail": paperbanana_check["detail"],
                "paper_ref": paperbanana_check["paper_ref"],
                "live_ref": paperbanana_check["live_ref"],
            }
        },
    }

    if not strict:
        return 0, result

    failures: list[str] = []
    if platforms["gh_pages"]["status"] not in {"success", "pending"}:
        failures.append("gh_pages")
    if devto_key and platforms["devto"]["status"] != "success":
        failures.append("devto")
    if linkedin_token and platforms["linkedin"]["status"] != "success":
        failures.append("linkedin")
    if not x_missing and platforms["x"]["status"] != "success":
        failures.append("x")
    if paperbanana_check["status"] != "success":
        failures.append("paperbanana_in_report")
    if failures:
        result["strict_failures"] = failures
        return 1, result
    return 0, result


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish daily report to all blog channels")
    parser.add_argument(
        "--report",
        required=True,
        help="Path to daily report markdown file (e.g., docs/_reports/YYYY-MM-DD-daily-report.md)",
    )
    parser.add_argument("--date", help="Report date override (YYYY-MM-DD)")
    parser.add_argument(
        "--strict", action="store_true", help="Fail when enabled platform publish fails"
    )
    parser.add_argument("--dry-run-x", action="store_true", help="Dry-run X publish only")
    parser.add_argument("--site-url", default=DEFAULT_SITE_URL, help="Canonical site base URL")
    args = parser.parse_args()

    report_path = Path(args.report)
    exit_code, result = publish_daily_report(
        report_path,
        report_date=args.date,
        site_url=args.site_url.rstrip("/"),
        strict=args.strict,
        dry_run=args.dry_run_x,
    )

    report_date = str(result.get("date", datetime.now(ET).date().isoformat()))
    status_json = PROJECT_ROOT / "data" / "analytics" / f"{report_date}-publication-status.json"
    status_jsonl = PROJECT_ROOT / "data" / "analytics" / "publication-status-history.jsonl"
    md_report = PROJECT_ROOT / "docs" / "_reports" / f"{report_date}-publication-status.md"
    agents_md_report = PROJECT_ROOT / "docs" / "_reports" / f"{report_date}-daily-report.agents.md"
    timeline_json = PROJECT_ROOT / "docs" / "data" / "content_timeline.json"
    beats_page = PROJECT_ROOT / "docs" / "beats.md"

    _write_json(status_json, result)
    _append_jsonl(status_jsonl, result)
    _write_markdown_report(md_report, result)
    _write_agents_markdown_report(agents_md_report, result)
    timeline_rows = _upsert_timeline_entry(
        timeline_json,
        {
            "id": f"daily-report:{report_date}",
            "date": report_date,
            "title": str(result.get("title", "")),
            "canonical_url": str(result.get("canonical_url", "")),
            "generated_at_utc": str(result.get("generated_at_utc", "")),
            "platforms": result.get("platforms", {}),
            "paperbanana_refs": {
                "paper": str(result.get("verification", {}).get("paperbanana_in_report", {}).get("paper_ref", "")),
                "live": str(result.get("verification", {}).get("paperbanana_in_report", {}).get("live_ref", "")),
            },
        },
    )
    _write_beats_page(beats_page, timeline_rows)

    print(json.dumps(result, indent=2))
    print(f"Wrote status JSON: {status_json}")
    print(f"Appended status history: {status_jsonl}")
    print(f"Wrote status report: {md_report}")
    print(f"Wrote agent markdown report: {agents_md_report}")
    print(f"Wrote content timeline JSON: {timeline_json}")
    print(f"Wrote beats page: {beats_page}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

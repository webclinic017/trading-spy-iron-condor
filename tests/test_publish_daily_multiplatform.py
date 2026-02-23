from __future__ import annotations

from datetime import datetime
from pathlib import Path

import scripts.publish_daily_multiplatform as publish


class _FakeResponse:
    def __init__(self, status_code: int, url: str, text: str = "") -> None:
        self.status_code = status_code
        self.url = url
        self.text = text


def _write_report(path: Path, canonical_url: str) -> None:
    path.write_text(
        "\n".join(
            [
                "---",
                'title: "Daily Report"',
                f'canonical_url: "{canonical_url}"',
                "tags:",
                "  - ai",
                "---",
                "",
                "## Alpaca Snapshot + PaperBanana Technical Narrative",
                "",
                "| Alpaca Snapshot | PaperBanana Financial Diagram |",
                "| --- | --- |",
                "| ![Paper](/trading/assets/snapshots/alpaca_paper_latest.png) | ![Paper Diagram](/trading/assets/snapshots/paperbanana_paper_latest.svg) |",
                "| ![Brokerage](/trading/assets/snapshots/alpaca_live_latest.png) | ![Brokerage Diagram](/trading/assets/snapshots/paperbanana_live_latest.svg) |",
            ]
        ),
        encoding="utf-8",
    )


def test_publish_daily_report_marks_gh_pages_pending_for_today(monkeypatch, tmp_path: Path) -> None:
    report_path = tmp_path / "2026-02-23-daily-report.md"
    canonical = "https://example.com/reports/2026-02-23-daily-report/"
    _write_report(report_path, canonical)

    today_et = datetime.now(publish.ET).date().isoformat()

    def fake_get(url: str, **_: object) -> _FakeResponse:
        if url == canonical:
            return _FakeResponse(404, canonical, "not found")
        raise AssertionError(f"unexpected URL requested: {url}")

    monkeypatch.setattr(publish.requests, "get", fake_get)
    monkeypatch.delenv("DEVTO_API_KEY", raising=False)
    monkeypatch.delenv("DEV_TO_API_KEY", raising=False)
    monkeypatch.delenv("LINKEDIN_ACCESS_TOKEN", raising=False)

    exit_code, result = publish.publish_daily_report(
        report_path,
        report_date=today_et,
        strict=False,
    )

    assert exit_code == 0
    assert result["platforms"]["gh_pages"]["status"] == "pending"
    assert result["verification"]["paperbanana_in_report"]["status"] == "success"


def test_publish_daily_report_strict_fails_when_devto_missing_diagrams(
    monkeypatch, tmp_path: Path
) -> None:
    report_path = tmp_path / "2026-02-21-daily-report.md"
    canonical = "https://example.com/reports/2026-02-21-daily-report/"
    _write_report(report_path, canonical)

    devto_url = "https://dev.to/example/post"

    def fake_get(url: str, **_: object) -> _FakeResponse:
        if url == canonical:
            return _FakeResponse(200, canonical, "ok")
        if url == devto_url:
            return _FakeResponse(200, devto_url, "<html><body>No diagrams</body></html>")
        raise AssertionError(f"unexpected URL requested: {url}")

    monkeypatch.setattr(publish.requests, "get", fake_get)
    monkeypatch.setattr(publish, "publish_to_devto", lambda *_args, **_kwargs: devto_url)
    monkeypatch.setenv("DEVTO_API_KEY", "test")
    monkeypatch.delenv("LINKEDIN_ACCESS_TOKEN", raising=False)

    exit_code, result = publish.publish_daily_report(
        report_path,
        report_date="2026-02-21",
        strict=True,
    )

    assert exit_code == 1
    assert result["platforms"]["devto"]["status"] == "failed"
    assert "strict_failures" in result
    assert "devto" in result["strict_failures"]


def test_timeline_upsert_and_beats_page(monkeypatch, tmp_path: Path) -> None:
    timeline_path = tmp_path / "content_timeline.json"
    beats_path = tmp_path / "beats.md"

    entry = {
        "id": "daily-report:2026-02-21",
        "date": "2026-02-21",
        "title": "Daily Report",
        "canonical_url": "https://example.com/reports/2026-02-21-daily-report/",
        "generated_at_utc": "2026-02-21T20:00:00Z",
        "platforms": {
            "gh_pages": {"status": "success"},
            "devto": {"status": "success", "url": "https://dev.to/example/post"},
            "linkedin": {"status": "skipped"},
            "x": {"status": "skipped"},
        },
        "paperbanana_refs": {
            "paper": "paperbanana_paper_latest.svg",
            "live": "paperbanana_live_latest.svg",
        },
    }

    rows = publish._upsert_timeline_entry(timeline_path, entry)
    publish._write_beats_page(beats_path, rows)

    timeline_text = timeline_path.read_text(encoding="utf-8")
    beats_text = beats_path.read_text(encoding="utf-8")

    assert "daily-report:2026-02-21" in timeline_text
    assert "# Beats" in beats_text
    assert "`devto`" in beats_text
    assert "paperbanana_paper_latest.svg" in beats_text

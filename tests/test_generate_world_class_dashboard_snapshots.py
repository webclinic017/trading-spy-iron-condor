from scripts.generate_world_class_dashboard_enhanced import build_alpaca_snapshot_markdown


def test_build_alpaca_snapshot_markdown_includes_manifest_values() -> None:
    manifest = {
        "latest": {
            "alpaca_paper": {
                "url": "/trading/assets/snapshots/alpaca_paper_latest.png",
                "captured_at_utc": "2026-02-16T19:10:10Z",
            },
            "alpaca_live": {
                "url": "/trading/assets/snapshots/alpaca_live_latest.png",
                "captured_at_utc": "2026-02-16T19:10:11Z",
            },
            "progress": {
                "url": "/trading/assets/snapshots/progress_latest.png",
                "captured_at_utc": "2026-02-16T19:10:12Z",
            },
        }
    }

    text = build_alpaca_snapshot_markdown(manifest)

    assert "Alpaca Snapshot Evidence" in text
    assert "/trading/assets/snapshots/alpaca_paper_latest.png" in text
    assert "/trading/assets/snapshots/alpaca_live_latest.png" in text
    assert "/trading/assets/snapshots/progress_latest.png" in text
    assert "2026-02-16T19:10:10Z" in text

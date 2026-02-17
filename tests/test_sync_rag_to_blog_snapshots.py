import json

from scripts import sync_rag_to_blog


def test_alpaca_snapshot_section_for_post_uses_manifest(tmp_path) -> None:
    manifest_path = tmp_path / "alpaca_snapshots.json"
    manifest_path.write_text(
        json.dumps(
            {
                "latest": {
                    "alpaca_paper": {
                        "url": "/trading/assets/snapshots/alpaca_paper_latest.png",
                        "diagram_url": "/trading/assets/snapshots/paperbanana_paper_latest.svg",
                        "captured_at_utc": "2026-02-16T19:10:10Z",
                        "technical_explainer": "paper summary",
                    },
                    "alpaca_live": {
                        "url": "/trading/assets/snapshots/alpaca_live_latest.png",
                        "diagram_url": "/trading/assets/snapshots/paperbanana_live_latest.svg",
                        "captured_at_utc": "2026-02-16T19:10:11Z",
                        "technical_explainer": "live summary",
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    original = sync_rag_to_blog.SNAPSHOT_MANIFEST_PATH
    try:
        sync_rag_to_blog.SNAPSHOT_MANIFEST_PATH = manifest_path
        section = sync_rag_to_blog._alpaca_snapshot_section_for_post()
    finally:
        sync_rag_to_blog.SNAPSHOT_MANIFEST_PATH = original

    assert "Alpaca Snapshot + PaperBanana Technical Narrative" in section
    assert "paper summary" in section
    assert "live summary" in section

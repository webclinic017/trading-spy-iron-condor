from scripts import generate_daily_blog_post as daily_blog


def test_generate_alpaca_visual_evidence_section_has_pairing_defaults() -> None:
    section = daily_blog.generate_alpaca_visual_evidence_section()
    assert "Alpaca Snapshot + PaperBanana Technical Narrative" in section
    assert "/trading/assets/snapshots/alpaca_paper_latest.png" in section
    assert "/trading/assets/snapshots/paperbanana_paper_latest.svg" in section
    assert "/trading/assets/snapshots/alpaca_live_latest.png" in section
    assert "/trading/assets/snapshots/paperbanana_live_latest.svg" in section

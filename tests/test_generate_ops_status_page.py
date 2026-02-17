from scripts.generate_ops_status_page import _normalize_metric_rows


def test_normalize_metric_rows_overrides_conflicting_values() -> None:
    rows = [
        ("Win Rate", "37.50%", "WARN", "sample_size=32"),
        ("Gateway Latency", "997 ms", "PASS", "from old cache"),
        ("Gateway Cost (smoke call)", "$0.000045", "PASS", "stale"),
    ]

    html = _normalize_metric_rows(
        metrics=rows,
        latency_ms="1626",
        cost_usd="0.00004500",
        win_rate=100.0,
        sample_size=1,
    )

    assert "1626 ms" in html
    assert "$0.00004500" in html
    assert "sample_size=1" in html
    assert "100.00%" in html

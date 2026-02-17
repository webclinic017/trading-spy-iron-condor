from scripts.capture_trading_screenshots import resolve_account_credentials


def test_resolve_paper_credentials_prefers_paper_specific_keys() -> None:
    env = {
        "ALPACA_PAPER_TRADING_API_KEY": "paper_key",
        "ALPACA_PAPER_TRADING_API_SECRET": "paper_secret",
        "ALPACA_API_KEY": "fallback_key",
        "ALPACA_SECRET_KEY": "fallback_secret",
    }
    key, secret = resolve_account_credentials("paper", env)
    assert key == "paper_key"
    assert secret == "paper_secret"


def test_resolve_live_credentials_prefers_brokerage_keys() -> None:
    env = {
        "ALPACA_BROKERAGE_TRADING_API_KEY": "live_key",
        "ALPACA_BROKERAGE_TRADING_API_SECRET": "live_secret",
        "ALPACA_API_KEY": "fallback_key",
        "ALPACA_SECRET_KEY": "fallback_secret",
    }
    key, secret = resolve_account_credentials("live", env)
    assert key == "live_key"
    assert secret == "live_secret"


def test_resolve_credentials_falls_back_to_generic_keys() -> None:
    env = {
        "ALPACA_API_KEY": "generic_key",
        "ALPACA_SECRET_KEY": "generic_secret",
    }
    paper_key, paper_secret = resolve_account_credentials("paper", env)
    live_key, live_secret = resolve_account_credentials("live", env)
    assert (paper_key, paper_secret) == ("generic_key", "generic_secret")
    assert (live_key, live_secret) == ("generic_key", "generic_secret")

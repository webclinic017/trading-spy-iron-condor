"""
Tests for PreTradeValidator and validate_trade.

Covers:
- Valid trades (all allowed tickers, all allowed strategies)
- Blocked ticker
- Risk limit exceeded / boundary
- Position imbalance for spread strategies
- Disallowed strategy
- Multiple simultaneous validation failures
- Convenience function validate_trade()
- RAG advice fallback when import fails
- Custom account values
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.trading_constants import ALLOWED_TICKERS, MAX_POSITION_PCT
from src.utils.pre_trade_validator import (
    PreTradeValidationError,
    PreTradeValidator,
    validate_trade,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def validator():
    """Default validator with $100K account."""
    return PreTradeValidator(account_value=100_000.0)


@pytest.fixture
def small_validator():
    """Validator with minimum $5K account (default)."""
    return PreTradeValidator()


# ---------------------------------------------------------------------------
# Valid trade scenarios
# ---------------------------------------------------------------------------

class TestValidTrades:

    def test_spy_iron_condor_passes(self, validator):
        result = validator.validate(
            symbol="SPY",
            strategy="iron_condor",
            quantity=1,
            risk_amount=200.0,
            long_legs=2,
            short_legs=2,
        )
        assert result is True

    @pytest.mark.parametrize("ticker", sorted(ALLOWED_TICKERS))
    def test_all_allowed_tickers_pass(self, validator, ticker):
        result = validator.validate(
            symbol=ticker,
            strategy="iron_condor",
            quantity=1,
            risk_amount=100.0,
            long_legs=2,
            short_legs=2,
        )
        assert result is True

    @pytest.mark.parametrize(
        "strategy",
        ["iron_condor", "credit_spread", "put_spread", "call_spread"],
    )
    def test_all_allowed_strategies_pass(self, validator, strategy):
        result = validator.validate(
            symbol="SPY",
            strategy=strategy,
            quantity=1,
            risk_amount=100.0,
            long_legs=1,
            short_legs=1,
        )
        assert result is True

    def test_risk_exactly_at_limit(self, validator):
        """Risk amount equal to max_risk should pass (not exceed)."""
        max_risk = validator.max_risk  # 100_000 * 0.05 = 5000
        result = validator.validate(
            symbol="SPY",
            strategy="iron_condor",
            quantity=1,
            risk_amount=max_risk,
            long_legs=2,
            short_legs=2,
        )
        assert result is True

    def test_zero_risk_amount_passes(self, validator):
        result = validator.validate(
            symbol="SPY",
            strategy="iron_condor",
            quantity=1,
            risk_amount=0.0,
            long_legs=2,
            short_legs=2,
        )
        assert result is True

    def test_non_spread_strategy_skips_leg_balance_check(self, validator):
        """Strategies not in the spread list skip leg balance validation."""
        # iron_condor IS in the list, so use a workaround: the allowed_strategies
        # check catches unknown strategies. But credit_spread with unequal legs fails.
        # For non-spread allowed strategies, there are none that skip.
        # This test verifies that the leg check only applies to spread types.
        # All 4 allowed strategies are spread types, so we just confirm
        # that equal legs works for all of them.
        for strat in ["iron_condor", "credit_spread", "put_spread", "call_spread"]:
            result = validator.validate(
                symbol="SPY",
                strategy=strat,
                quantity=1,
                risk_amount=100.0,
                long_legs=3,
                short_legs=3,
            )
            assert result is True


# ---------------------------------------------------------------------------
# Blocked ticker
# ---------------------------------------------------------------------------

class TestTickerValidation:

    def test_blocked_ticker_sofi(self, validator):
        with pytest.raises(PreTradeValidationError, match="BLOCKED.*not in allowed tickers"):
            validator.validate(
                symbol="SOFI",
                strategy="iron_condor",
                quantity=1,
                risk_amount=100.0,
                long_legs=2,
                short_legs=2,
            )

    def test_blocked_ticker_aapl(self, validator):
        with pytest.raises(PreTradeValidationError, match="BLOCKED"):
            validator.validate(
                symbol="AAPL",
                strategy="credit_spread",
                quantity=1,
                risk_amount=100.0,
                long_legs=1,
                short_legs=1,
            )

    def test_option_symbol_extracts_base_via_split(self, validator):
        """The validator splits on '2' to extract base symbol.
        SPY260115C00600000 -> base 'SPY' (split on first '2' -> 'SPY').
        """
        # Symbol containing '2' gets split; 'SPY' is extracted as base
        result = validator.validate(
            symbol="SPY260115C00600000",
            strategy="iron_condor",
            quantity=1,
            risk_amount=100.0,
            long_legs=2,
            short_legs=2,
        )
        assert result is True

    def test_option_symbol_blocked_underlying(self, validator):
        """SOFI option symbol should be blocked."""
        with pytest.raises(PreTradeValidationError, match="not in allowed tickers"):
            validator.validate(
                symbol="SOFI260206P00024000",
                strategy="credit_spread",
                quantity=1,
                risk_amount=100.0,
                long_legs=1,
                short_legs=1,
            )

    def test_empty_string_ticker_blocked(self, validator):
        with pytest.raises(PreTradeValidationError, match="not in allowed tickers"):
            validator.validate(
                symbol="",
                strategy="iron_condor",
                quantity=1,
                risk_amount=100.0,
                long_legs=2,
                short_legs=2,
            )


# ---------------------------------------------------------------------------
# Risk limit
# ---------------------------------------------------------------------------

class TestRiskValidation:

    def test_risk_exceeds_limit(self, validator):
        """Risk > 5% of account should be blocked."""
        over_limit = validator.max_risk + 0.01
        with pytest.raises(PreTradeValidationError, match="exceeds 5% limit"):
            validator.validate(
                symbol="SPY",
                strategy="iron_condor",
                quantity=1,
                risk_amount=over_limit,
                long_legs=2,
                short_legs=2,
            )

    def test_risk_far_exceeds_limit(self, validator):
        with pytest.raises(PreTradeValidationError, match="Phil Town Rule #1"):
            validator.validate(
                symbol="SPY",
                strategy="iron_condor",
                quantity=1,
                risk_amount=50_000.0,
                long_legs=2,
                short_legs=2,
            )

    def test_small_account_risk_limit(self, small_validator):
        """Default $5K account: max risk = $250."""
        assert small_validator.max_risk == 5000.0 * MAX_POSITION_PCT
        with pytest.raises(PreTradeValidationError, match="exceeds 5% limit"):
            small_validator.validate(
                symbol="SPY",
                strategy="iron_condor",
                quantity=1,
                risk_amount=251.0,
                long_legs=2,
                short_legs=2,
            )

    def test_negative_risk_passes(self, validator):
        """Negative risk (credit received) should not trigger limit."""
        result = validator.validate(
            symbol="SPY",
            strategy="iron_condor",
            quantity=1,
            risk_amount=-100.0,
            long_legs=2,
            short_legs=2,
        )
        assert result is True


# ---------------------------------------------------------------------------
# Position balance (leg imbalance)
# ---------------------------------------------------------------------------

class TestLegBalance:

    def test_iron_condor_imbalanced_legs(self, validator):
        with pytest.raises(PreTradeValidationError, match="Position imbalance"):
            validator.validate(
                symbol="SPY",
                strategy="iron_condor",
                quantity=1,
                risk_amount=100.0,
                long_legs=6,
                short_legs=4,
            )

    def test_credit_spread_imbalanced_legs(self, validator):
        with pytest.raises(PreTradeValidationError, match="Position imbalance"):
            validator.validate(
                symbol="SPY",
                strategy="credit_spread",
                quantity=1,
                risk_amount=100.0,
                long_legs=1,
                short_legs=2,
            )

    def test_put_spread_imbalanced(self, validator):
        with pytest.raises(PreTradeValidationError, match="Position imbalance"):
            validator.validate(
                symbol="SPY",
                strategy="put_spread",
                quantity=1,
                risk_amount=100.0,
                long_legs=0,
                short_legs=1,
            )

    def test_call_spread_imbalanced(self, validator):
        with pytest.raises(PreTradeValidationError, match="Position imbalance"):
            validator.validate(
                symbol="SPY",
                strategy="call_spread",
                quantity=1,
                risk_amount=100.0,
                long_legs=2,
                short_legs=1,
            )

    def test_zero_legs_balanced(self, validator):
        """Both legs at 0 is technically balanced -- should pass."""
        result = validator.validate(
            symbol="SPY",
            strategy="iron_condor",
            quantity=1,
            risk_amount=100.0,
            long_legs=0,
            short_legs=0,
        )
        assert result is True


# ---------------------------------------------------------------------------
# Disallowed strategy
# ---------------------------------------------------------------------------

class TestStrategyValidation:

    @pytest.mark.parametrize(
        "bad_strategy",
        ["naked_put", "naked_call", "short_straddle", "short_strangle", "butterfly", ""],
    )
    def test_disallowed_strategies(self, validator, bad_strategy):
        with pytest.raises(PreTradeValidationError, match="not allowed"):
            validator.validate(
                symbol="SPY",
                strategy=bad_strategy,
                quantity=1,
                risk_amount=100.0,
                long_legs=1,
                short_legs=1,
            )


# ---------------------------------------------------------------------------
# Multiple simultaneous failures
# ---------------------------------------------------------------------------

class TestMultipleErrors:

    def test_bad_ticker_and_bad_strategy_and_risk(self, validator):
        """All checks fail at once -- error message contains all failures."""
        with pytest.raises(PreTradeValidationError) as exc_info:
            validator.validate(
                symbol="TSLA",
                strategy="naked_call",
                quantity=1,
                risk_amount=999_999.0,
                long_legs=1,
                short_legs=1,
            )
        msg = str(exc_info.value)
        assert "not in allowed tickers" in msg
        assert "exceeds 5% limit" in msg
        assert "not allowed" in msg

    def test_bad_ticker_and_imbalanced_legs(self, validator):
        with pytest.raises(PreTradeValidationError) as exc_info:
            validator.validate(
                symbol="GME",
                strategy="iron_condor",
                quantity=1,
                risk_amount=100.0,
                long_legs=3,
                short_legs=1,
            )
        msg = str(exc_info.value)
        assert "not in allowed tickers" in msg
        assert "Position imbalance" in msg


# ---------------------------------------------------------------------------
# Convenience function validate_trade()
# ---------------------------------------------------------------------------

class TestValidateTradeFunction:

    def test_valid_trade(self):
        result = validate_trade(
            symbol="SPY",
            strategy="iron_condor",
            quantity=1,
            risk_amount=200.0,
            long_legs=2,
            short_legs=2,
            account_value=100_000.0,
        )
        assert result is True

    def test_invalid_trade_raises(self):
        with pytest.raises(PreTradeValidationError):
            validate_trade(
                symbol="SOFI",
                strategy="iron_condor",
                quantity=1,
                risk_amount=200.0,
                long_legs=2,
                short_legs=2,
            )

    def test_defaults_work(self):
        """Default arguments (quantity=1, risk_amount=0, legs=0, account=5000) should pass."""
        result = validate_trade(symbol="SPY", strategy="iron_condor")
        assert result is True

    def test_custom_account_value(self):
        """With a $1000 account, max risk = $50. $51 should fail."""
        with pytest.raises(PreTradeValidationError, match="exceeds 5% limit"):
            validate_trade(
                symbol="SPY",
                strategy="iron_condor",
                quantity=1,
                risk_amount=51.0,
                account_value=1000.0,
            )


# ---------------------------------------------------------------------------
# Constructor / account_value
# ---------------------------------------------------------------------------

class TestConstructor:

    def test_default_account_value(self):
        v = PreTradeValidator()
        assert v.account_value == 5000.0
        assert v.max_risk == 5000.0 * MAX_POSITION_PCT

    def test_custom_account_value(self):
        v = PreTradeValidator(account_value=200_000.0)
        assert v.account_value == 200_000.0
        assert v.max_risk == 200_000.0 * MAX_POSITION_PCT

    def test_zero_account_value(self):
        v = PreTradeValidator(account_value=0.0)
        assert v.max_risk == 0.0
        # Any positive risk should fail
        with pytest.raises(PreTradeValidationError, match="exceeds 5% limit"):
            v.validate(
                symbol="SPY",
                strategy="iron_condor",
                quantity=1,
                risk_amount=0.01,
                long_legs=2,
                short_legs=2,
            )

    def test_min_win_rate_class_attribute(self):
        assert PreTradeValidator.MIN_WIN_RATE == 0.80


# ---------------------------------------------------------------------------
# RAG advice
# ---------------------------------------------------------------------------

class TestGetRagAdvice:

    def test_rag_unavailable_returns_fallback(self, validator):
        """When RAG import fails, returns cautionary message."""
        with patch.dict("sys.modules", {"src.rag.lessons_learned_rag": None}):
            result = validator.get_rag_advice("SPY", "iron_condor")
            assert "RAG unavailable" in result

    def test_rag_success(self, validator):
        mock_lesson = MagicMock()
        mock_lesson.title = "LL-220"
        mock_lesson.snippet = "15-delta SPY iron condors have 86% win rate historically"

        mock_rag_module = MagicMock()
        mock_rag_instance = MagicMock()
        mock_rag_instance.search.return_value = [(mock_lesson, 0.95)]
        mock_rag_module.LessonsLearnedRAG.return_value = mock_rag_instance

        with patch.dict("sys.modules", {"src.rag.lessons_learned_rag": mock_rag_module}):
            result = validator.get_rag_advice("SPY", "iron_condor")
            assert "RAG ADVICE" in result
            assert "LL-220" in result

    def test_rag_exception_returns_fallback(self, validator):
        mock_rag_module = MagicMock()
        mock_rag_module.LessonsLearnedRAG.side_effect = RuntimeError("DB connection failed")

        with patch.dict("sys.modules", {"src.rag.lessons_learned_rag": mock_rag_module}):
            result = validator.get_rag_advice("SPY", "iron_condor")
            assert "RAG unavailable" in result


# ---------------------------------------------------------------------------
# PreTradeValidationError
# ---------------------------------------------------------------------------

class TestPreTradeValidationError:

    def test_is_exception(self):
        assert issubclass(PreTradeValidationError, Exception)

    def test_message_preserved(self):
        err = PreTradeValidationError("test error")
        assert str(err) == "test error"

from src.safety.multi_model_juror import MultiModelJuror


def test_juror_consensus_agree():
    juror = MultiModelJuror()
    proposal = {"symbol": "SPY", "strategy": "iron_condor", "amount": 500.0}
    reasoning = "VIX is optimal, 15-delta selected."

    # In the MVP, it simulates an 'AGREE' response.
    # We test that the default MVP behavior successfully returns True.
    result = juror.get_consensus(proposal, primary_reasoning=reasoning)

    assert result is True


def test_juror_consensus_exception_fails_closed(monkeypatch):
    juror = MultiModelJuror()
    proposal = {"symbol": "SPY"}

    # Mock the internal logic to raise an exception and prove it fails CLOSED
    with monkeypatch.context() as m:
        m.setattr(juror, "selector", None)  # Force an error if accessed, or mock log

        # We can just mock the logging or execution to raise an error
        def mock_error(*args, **kwargs):
            raise RuntimeError("API Offline")

        m.setattr("src.safety.multi_model_juror.logger.info", mock_error)

        result = juror.get_consensus(proposal, "test reasoning")
        assert result is False  # Must fail closed on exception

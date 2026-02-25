import pytest
from unittest.mock import MagicMock, patch
from src.strategies.iron_condor.signal import IronCondorSignal

@patch("src.strategies.iron_condor.signal.VIXMeanReversionSignal")
def test_signal_entry_vix_optimal(mock_vix):
    mock_vix_inst = mock_vix.return_value
    mock_vix_inst.calculate_signal.return_value = MagicMock(
        signal="GOOD_ENTRY", 
        confidence=0.85,
        reason="VIX optimal regime"
    )
    
    signal = IronCondorSignal()
    market_data = {"symbol": "SPY"}
    result = signal.generate_signal(market_data)
    assert result.should_entry is True
    assert "optimal regime" in result.reason

@patch("src.strategies.iron_condor.signal.VIXMeanReversionSignal")
def test_signal_reject_vix_extreme(mock_vix):
    mock_vix_inst = mock_vix.return_value
    mock_vix_inst.calculate_signal.return_value = MagicMock(
        signal="AVOID", 
        confidence=0.0,
        reason="regime unfavorable"
    )
    
    signal = IronCondorSignal()
    market_data = {"symbol": "SPY"}
    result = signal.generate_signal(market_data)
    assert result.should_entry is False
    assert "unfavorable" in result.reason

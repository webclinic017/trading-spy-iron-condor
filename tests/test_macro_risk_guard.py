from src.safety.macro_risk_guard import MacroRiskGuard

def test_macro_guard_oil_spike():
    guard = MacroRiskGuard()
    # 10% spike in oil
    vitals = {"oil_change": 0.10, "oil_price": 85.0, "yield_change": 0.01}
    safe, reason = guard.check_macro_vitals(vitals)
    assert safe is False
    assert "Oil spike" in reason

def test_macro_guard_oil_price_limit():
    guard = MacroRiskGuard()
    # Oil at $105
    vitals = {"oil_change": 0.01, "oil_price": 105.0, "yield_change": 0.01}
    safe, reason = guard.check_macro_vitals(vitals)
    assert safe is False
    assert "Oil spike" in reason # Or price threshold

def test_macro_guard_yield_spike():
    guard = MacroRiskGuard()
    # 6% move in yields
    vitals = {"oil_change": 0.01, "oil_price": 75.0, "yield_change": 0.06}
    safe, reason = guard.check_macro_vitals(vitals)
    assert safe is False
    assert "Fiscal" in reason.upper() or "Yield" in reason

def test_macro_guard_normal_conditions():
    guard = MacroRiskGuard()
    vitals = {"oil_change": 0.01, "oil_price": 75.0, "yield_change": 0.01}
    safe, reason = guard.check_macro_vitals(vitals)
    assert safe is True
    assert reason == ""

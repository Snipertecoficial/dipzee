"""Unit tests for the Opportunity Score engine — the core product logic.

Pure math, no I/O. Values are computed by hand from SETTINGS
(weights buy/upside/income = 0.45/0.35/0.20; upside cap 0.60; income cap 0.06).
"""
from scoring import compute_opportunity_score, classify


def test_none_when_insufficient_data():
    assert compute_opportunity_score(None, 10, 20, None, None) is None
    assert compute_opportunity_score(10, None, 20, None, None) is None
    assert compute_opportunity_score(10, 20, 20, None, None) is None  # H == L


def test_price_at_low_is_strong_buy():
    # P=L=10, H=20, no target, no dividend:
    # R=0 -> S_buy=100; upside_high=1.0 -> U=1.0 -> S_up=100; S_div=0
    # score = 0.45*100 + 0.35*100 + 0.20*0 = 80 -> strong_buy
    r = compute_opportunity_score(10, 10, 20, None, 0)
    assert r["score"] == 80
    assert r["classification"] == "strong_buy"
    assert r["flags"]["buy_zone"] is True
    assert r["flags"]["sell_zone"] is False


def test_price_at_high_is_sell():
    # P=H=20, L=10: R=1 -> S_buy=0; upside_high=0 -> S_up=0 -> score 0 -> sell
    r = compute_opportunity_score(20, 10, 20, None, 0)
    assert r["score"] == 0
    assert r["classification"] == "sell"
    assert r["flags"]["sell_zone"] is True


def test_dividend_income_flag_and_subscore():
    # D = 0.06 == income cap -> S_div = 100; D >= 0.04 -> income flag True
    r = compute_opportunity_score(15, 10, 20, None, 0.06)
    assert r["sub_scores"]["income"] == 100
    assert r["flags"]["income"] is True


def test_target_boosts_upside():
    # A target above price raises the upside sub-score vs. no target.
    with_target = compute_opportunity_score(10, 10, 20, 30, 0)
    without = compute_opportunity_score(10, 10, 20, None, 0)
    assert with_target["sub_scores"]["upside"] >= without["sub_scores"]["upside"]
    assert with_target["upside_target"] is not None


def test_score_always_in_range_and_int():
    for args in [(10, 10, 20, 30, 0.05), (18, 10, 20, 19, 0.0), (12, 10, 20, None, 0.03)]:
        r = compute_opportunity_score(*args)
        assert isinstance(r["score"], int)
        assert 0 <= r["score"] <= 100


def test_classify_thresholds():
    assert classify(85) == "strong_buy"
    assert classify(70) == "buy"
    assert classify(50) == "hold"
    assert classify(30) == "reduce"
    assert classify(10) == "sell"

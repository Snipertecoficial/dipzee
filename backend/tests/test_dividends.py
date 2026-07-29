"""Unit tests for dividend-yield normalization (providers.normalize_dividend_yield).

Guards the yfinance path that serves the dividend yield for most assets: the
decimal-vs-percent disambiguation, the preference for the forward yield
(rate/price), and the anti-mis-scaling clamp.
"""
import providers


def n(**info):
    return providers.normalize_dividend_yield(info)


def test_prefers_forward_yield_when_sane():
    # rate/price = 2.12/88.27 = 0.024; reported percent 2.52 -> forward preferred.
    v = n(dividendYield=2.52, dividendRate=2.12, currentPrice=88.27)
    assert round(v, 4) == 0.024


def test_percent_reported_descaled_when_no_rate():
    # 2.52 (percent) with no rate -> 0.0252, not 2.52.
    assert n(dividendYield=2.52) == 0.0252


def test_decimal_reported_kept_when_no_rate():
    assert n(dividendYield=0.0252) == 0.0252


def test_sub_one_percent_missing_rate_is_rescaled():
    # 0.51 means 0.51% (percent), not 51% — the clamp must rescale it.
    assert n(dividendYield=0.51) == 0.0051


def test_missing_yield_uses_forward():
    assert round(n(dividendRate=3.25, currentPrice=65.73), 4) == 0.0494


def test_mis_scaled_huge_value_rescaled():
    # Garbage 250 (no rate): de-scaled to 2.5, still insane -> rescaled to 0.025.
    assert n(dividendYield=250) == 0.025


def test_none_yields_zero():
    assert n() == 0.0
    assert n(dividendYield=None, dividendRate=None) == 0.0


def test_zero_dividend_non_payer():
    assert n(dividendYield=0.0, currentPrice=300) == 0.0


def test_insane_forward_falls_back_to_reported():
    # Bad rate (implied 900%) is rejected; the sane reported yield is used.
    v = n(dividendYield=3.0, dividendRate=900, currentPrice=100)
    assert v == 0.03

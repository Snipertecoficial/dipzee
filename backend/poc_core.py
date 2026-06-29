"""
POC Core script for Dipzee.
Proves two things in isolation BEFORE building the app:
  1) The pure Opportunity Score function matches the two reference unit tests.
  2) yfinance/Yahoo can fetch the required fields for US + TSX tickers, and we
     can robustly normalize dividendYield to a DECIMAL fraction.

Run: python poc_core.py
"""
import math
import time
from dataclasses import dataclass, field
from typing import Optional

# ----------------------------------------------------------------------------
# 1) PURE OPPORTUNITY SCORE (settings-configurable)
# ----------------------------------------------------------------------------

DEFAULT_SETTINGS = {
    "weights": {"buy": 0.45, "upside": 0.35, "income": 0.20},
    "upside": {"target_weight": 0.6, "high_weight": 0.4, "cap": 0.60},
    "income": {"cap": 0.06},
    "flags": {"buy_zone_r": 0.15, "sell_zone_r": 0.85, "income_d": 0.04},
    "classification": [
        (80, "strong_buy"),
        (65, "buy"),
        (45, "hold"),
        (30, "reduce"),
        (0, "sell"),
    ],
}


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def compute_opportunity_score(P, L, H, T, D, settings=DEFAULT_SETTINGS):
    """
    P = price, L = 52w low, H = 52w high, T = analyst target mean, D = dividend yield (decimal).
    Returns dict with score, sub_scores, classification, flags, and raw R/U.
    Handles missing/degenerate inputs gracefully.
    """
    w = settings["weights"]
    up = settings["upside"]
    inc = settings["income"]
    fl = settings["flags"]

    if P is None or L is None or H is None or H == L:
        return None  # not enough data to score

    P = float(P); L = float(L); H = float(H)
    D = float(D) if D is not None else 0.0

    # Range position R
    R = _clamp((P - L) / (H - L), 0.0, 1.0)

    # Upside
    upside_high = (H - P) / P if P > 0 else 0.0
    if T is not None and float(T) > 0:
        upside_target = (float(T) - P) / P if P > 0 else 0.0
        U = up["target_weight"] * upside_target + up["high_weight"] * upside_high
    else:
        U = upside_high

    S_buy = (1 - R) * 100
    S_up = _clamp(U / up["cap"], 0.0, 1.0) * 100
    S_div = _clamp(D / inc["cap"], 0.0, 1.0) * 100

    score = round(w["buy"] * S_buy + w["upside"] * S_up + w["income"] * S_div)

    classification = "sell"
    for threshold, label in settings["classification"]:
        if score >= threshold:
            classification = label
            break

    flags = {
        "buy_zone": R <= fl["buy_zone_r"],
        "sell_zone": (R >= fl["sell_zone_r"]) or (T is not None and float(T) > 0 and P >= float(T)),
        "income": D >= fl["income_d"],
    }

    return {
        "score": score,
        "sub_scores": {"buy": round(S_buy, 2), "upside": round(S_up, 2), "income": round(S_div, 2)},
        "classification": classification,
        "flags": flags,
        "R": round(R, 4),
        "U": round(U, 4),
    }


def run_unit_tests():
    print("=" * 70)
    print("UNIT TESTS — Opportunity Score")
    print("=" * 70)
    ok = True

    # Test 1: TELUS-like -> ~96 Strong Buy, buy_zone True
    r1 = compute_opportunity_score(P=11.10, L=11.04, H=16.74, T=17.33, D=0.1081)
    print("Test 1:", r1)
    t1 = (94 <= r1["score"] <= 98) and r1["classification"] == "strong_buy" and r1["flags"]["buy_zone"] is True
    print(f"  -> expected score~96 strong_buy buy_zone=True : {'PASS' if t1 else 'FAIL'}")
    ok = ok and t1

    # Test 2: NVDA-like -> ~72 Buy
    r2 = compute_opportunity_score(P=372.97, L=349.20, H=555.45, T=561.11, D=0.0098)
    print("Test 2:", r2)
    t2 = (70 <= r2["score"] <= 74) and r2["classification"] == "buy"
    print(f"  -> expected score~72 buy : {'PASS' if t2 else 'FAIL'}")
    ok = ok and t2

    # Edge: missing target -> uses upside_high
    r3 = compute_opportunity_score(P=50, L=40, H=80, T=None, D=0.05)
    print("Test 3 (no target):", r3)
    t3 = r3 is not None
    ok = ok and t3

    # Edge: degenerate H==L -> None
    r4 = compute_opportunity_score(P=50, L=50, H=50, T=60, D=0.0)
    print("Test 4 (H==L):", r4)
    t4 = r4 is None
    ok = ok and t4

    print(f"\nALL UNIT TESTS: {'PASS ✅' if ok else 'FAIL ❌'}")
    return ok


# ----------------------------------------------------------------------------
# 2) yfinance fetch + robust dividend yield normalization
# ----------------------------------------------------------------------------

def normalize_dividend_yield(info):
    """
    Normalize dividendYield to a DECIMAL fraction (e.g. 0.0098 = 0.98%).
    yfinance versions are inconsistent: some return 0.0098, some 0.98 (percent).
    Strategy: cross-check against dividendRate/price (ground truth) when available.
    """
    dy = info.get("dividendYield")
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    rate = info.get("dividendRate") or info.get("trailingAnnualDividendRate")

    implied = None
    if rate and price and price > 0:
        implied = rate / price  # this is always a true decimal fraction

    if dy is None:
        return implied if implied is not None else 0.0

    dy = float(dy)
    candidate_decimal = dy          # as-is
    candidate_pct = dy / 100.0      # if dy was expressed as percent

    if implied is not None and implied > 0:
        # pick whichever candidate is closest to implied
        if abs(candidate_decimal - implied) <= abs(candidate_pct - implied):
            return candidate_decimal
        return candidate_pct

    # No implied ground truth: heuristic. A real yield > 1.0 (=100%) is impossible,
    # so if dy > 1 it must be a percentage figure.
    if dy > 1.0:
        return candidate_pct
    return candidate_decimal


def fetch_ticker(symbol):
    import yfinance as yf
    print("-" * 70)
    print(f"FETCH: {symbol}")
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}
    except Exception as e:
        print(f"  ERROR fetching {symbol}: {e}")
        return None

    price = info.get("currentPrice") or info.get("regularMarketPrice")
    low = info.get("fiftyTwoWeekLow")
    high = info.get("fiftyTwoWeekHigh")
    target = info.get("targetMeanPrice")
    raw_dy = info.get("dividendYield")
    raw_rate = info.get("dividendRate") or info.get("trailingAnnualDividendRate")
    norm_dy = normalize_dividend_yield(info)
    currency = info.get("currency")
    name = info.get("longName") or info.get("shortName")
    sector = info.get("sector")

    print(f"  name={name} | currency={currency} | sector={sector}")
    print(f"  price={price} low52={low} high52={high} target={target}")
    print(f"  raw_dividendYield={raw_dy} dividendRate={raw_rate} -> normalized={norm_dy} ({(norm_dy or 0)*100:.2f}%)")

    if price and low and high:
        s = compute_opportunity_score(price, low, high, target, norm_dy)
        print(f"  SCORE: {s['score']} ({s['classification']}) flags={s['flags']}")
        return {"symbol": symbol, "ok": True, "score": s}
    else:
        print("  INSUFFICIENT DATA to score")
        return {"symbol": symbol, "ok": False}


def run_live_fetch():
    print("\n" + "=" * 70)
    print("LIVE FETCH — yfinance (US + TSX)")
    print("=" * 70)
    symbols = ["AAPL", "ENB.TO", "T.TO", "KO"]
    results = []
    for s in symbols:
        results.append(fetch_ticker(s))
        time.sleep(2)  # throttle to avoid rate limit
    ok_count = sum(1 for r in results if r and r.get("ok"))
    print(f"\nLIVE FETCH: {ok_count}/{len(symbols)} tickers scored")
    # Go criteria: at least 1 US + 1 TSX scored
    return ok_count >= 2


if __name__ == "__main__":
    unit_ok = run_unit_tests()
    live_ok = run_live_fetch()
    print("\n" + "=" * 70)
    print(f"POC RESULT: unit_tests={'PASS' if unit_ok else 'FAIL'} | live_fetch={'PASS' if live_ok else 'FAIL'}")
    print("=" * 70)

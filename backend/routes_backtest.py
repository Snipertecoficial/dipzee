"""Strategy backtest (Investor feature) — v2.

Two illustrative strategies, computed purely on daily closes with no lookahead:

* ``buy_the_dip``  — enter when the close is within ``dip`` of the trailing
  ``lookback``-day low (a buy-zone proxy) and exit ``hold_days`` later.
* ``sma_cross``    — hold while the short moving average is above the long one
  (a classic trend-following rule); stay in cash otherwise.

For both strategies we build a *daily equity curve* for the strategy and for a
naive buy-and-hold, so the frontend can chart them side by side. This is an
educational illustration of the "buy low / ride the trend" theses behind the
Opportunity Score — not investment advice.
"""
import math

from fastapi import APIRouter, Depends, Query

import market_service as ms
from security import require_feature

router = APIRouter(prefix="/backtest", tags=["backtest"])

STRATEGIES = {"buy_the_dip", "sma_cross"}


def _sma(prices, window):
    """Simple moving average; entries before the window is full are None."""
    out = [None] * len(prices)
    s = 0.0
    for i, p in enumerate(prices):
        s += p
        if i >= window:
            s -= prices[i - window]
        if i >= window - 1:
            out[i] = s / window
    return out


def _downsample(series, max_points=140):
    n = len(series)
    if n <= max_points:
        return series
    step = math.ceil(n / max_points)
    out = series[::step]
    if out[-1] is not series[-1]:
        out.append(series[-1])
    return out


def _max_drawdown(equity):
    peak = float("-inf")
    mdd = 0.0
    for v in equity:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (v - peak) / peak
            if dd < mdd:
                mdd = dd
    return mdd  # negative fraction


@router.get("")
async def run_backtest(
    ticker: str = Query(...),
    period: str = Query("2y"),
    strategy: str = Query("buy_the_dip"),
    lookback: int = Query(20, ge=5, le=120),
    dip: float = Query(0.03, ge=0.0, le=0.5),
    hold_days: int = Query(10, ge=1, le=120),
    short_ma: int = Query(20, ge=2, le=100),
    long_ma: int = Query(50, ge=5, le=250),
    _user: dict = Depends(require_feature("backtest")),
):
    ticker = ticker.strip().upper()
    strategy = strategy if strategy in STRATEGIES else "buy_the_dip"
    if strategy == "sma_cross" and short_ma >= long_ma:
        short_ma, long_ma = min(short_ma, long_ma - 1), max(long_ma, short_ma + 1)

    bars = ms.history(ticker, period=period, interval="1d")
    closes = [(b.get("date") or b.get("Date"), b.get("close")) for b in bars if b.get("close") is not None]
    n = len(closes)
    min_needed = (long_ma + 2) if strategy == "sma_cross" else (lookback + hold_days + 1)
    if n < min_needed:
        return {"ticker": ticker, "ok": False, "message": "not_enough_data", "bars": n}

    prices = [c[1] for c in closes]
    dates = [c[0] for c in closes]

    # in_market[i] == exposed to the return from day i-1 to day i.
    in_market = [False] * n
    trades = []

    if strategy == "sma_cross":
        sma_s = _sma(prices, short_ma)
        sma_l = _sma(prices, long_ma)
        sig = [False] * n
        for i in range(n):
            if sma_s[i] is not None and sma_l[i] is not None:
                sig[i] = sma_s[i] >= sma_l[i]
        for i in range(1, n):
            in_market[i] = sig[i - 1]  # act on yesterday's signal (no lookahead)
    else:  # buy_the_dip
        i = lookback
        while i < n - hold_days:
            window_low = min(prices[i - lookback:i])
            if window_low > 0 and prices[i] <= window_low * (1 + dip):
                for j in range(i + 1, i + hold_days + 1):
                    in_market[j] = True
                i = i + hold_days + 1  # non-overlapping
            else:
                i += 1

    # Derive discrete trades from in_market transitions (for the trade table).
    prev = False
    entry_i = None
    for i in range(1, n):
        cur = in_market[i]
        if cur and not prev:
            entry_i = i
        elif prev and not cur and entry_i is not None:
            e_idx, x_idx = entry_i - 1, i - 1
            ret = (prices[x_idx] - prices[e_idx]) / prices[e_idx] if prices[e_idx] else 0.0
            trades.append({
                "entry_date": dates[e_idx], "entry": round(prices[e_idx], 4),
                "exit_date": dates[x_idx], "exit": round(prices[x_idx], 4),
                "return_pct": round(ret * 100, 2),
            })
            entry_i = None
        prev = cur
    if prev and entry_i is not None:
        e_idx = entry_i - 1
        ret = (prices[-1] - prices[e_idx]) / prices[e_idx] if prices[e_idx] else 0.0
        trades.append({
            "entry_date": dates[e_idx], "entry": round(prices[e_idx], 4),
            "exit_date": dates[-1], "exit": round(prices[-1], 4),
            "return_pct": round(ret * 100, 2),
        })

    # Daily equity curves (base 100).
    strat_eq = [1.0] * n
    bh_eq = [1.0] * n
    for i in range(1, n):
        daily = (prices[i] / prices[i - 1] - 1) if prices[i - 1] else 0.0
        strat_eq[i] = strat_eq[i - 1] * (1 + (daily if in_market[i] else 0.0))
        bh_eq[i] = bh_eq[i - 1] * (1 + daily)

    curve = [
        {
            "date": (dates[i][:10] if isinstance(dates[i], str) else str(dates[i])),
            "strategy": round(strat_eq[i] * 100, 2),
            "buyhold": round(bh_eq[i] * 100, 2),
        }
        for i in range(n)
    ]
    curve = _downsample(curve, 140)

    wins = [t for t in trades if t["return_pct"] > 0]
    avg_ret = (sum(t["return_pct"] for t in trades) / len(trades)) if trades else 0.0
    time_in_market = round(sum(1 for x in in_market if x) / max(n - 1, 1) * 100, 1)

    return {
        "ticker": ticker,
        "ok": True,
        "params": {
            "period": period, "strategy": strategy, "lookback": lookback, "dip": dip,
            "hold_days": hold_days, "short_ma": short_ma, "long_ma": long_ma,
        },
        "bars": n,
        "start_date": dates[0],
        "end_date": dates[-1],
        "num_trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0.0,
        "avg_return_pct": round(avg_ret, 2),
        "strategy_return_pct": round((strat_eq[-1] - 1) * 100, 2),
        "buy_hold_return_pct": round((bh_eq[-1] - 1) * 100, 2),
        "max_drawdown_pct": round(_max_drawdown(strat_eq) * 100, 2),
        "time_in_market_pct": time_in_market,
        "equity_curve": curve,
        "trades": trades[-50:],
    }

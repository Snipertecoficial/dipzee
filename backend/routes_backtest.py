"""Simple strategy backtest (Investor feature).

Strategy ("buy the dip"): using daily closes, when the close is within
`dip`% of the trailing `lookback`-day low (a buy-zone proxy), enter a position
and exit `hold_days` later. Trades are non-overlapping. We report trade stats
and compare the strategy return against buy-and-hold over the same window.

This runs entirely on price history (no lookahead) so it is a fair, if simple,
illustration of the "buy low" thesis behind the Opportunity Score.
"""
from fastapi import APIRouter, Depends, Query

import market_service as ms
from security import require_feature

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.get("")
async def run_backtest(
    ticker: str = Query(...),
    period: str = Query("2y"),
    lookback: int = Query(20, ge=5, le=120),
    dip: float = Query(0.03, ge=0.0, le=0.5),
    hold_days: int = Query(10, ge=1, le=120),
    _user: dict = Depends(require_feature("backtest")),
):
    ticker = ticker.strip().upper()
    bars = ms.history(ticker, period=period, interval="1d")
    closes = [(b.get("date") or b.get("Date"), b.get("close")) for b in bars if b.get("close") is not None]
    n = len(closes)
    if n < lookback + hold_days + 1:
        return {"ticker": ticker, "ok": False, "message": "not_enough_data", "bars": n}

    prices = [c[1] for c in closes]
    dates = [c[0] for c in closes]
    trades = []
    i = lookback
    while i < n - hold_days:
        window_low = min(prices[i - lookback:i])
        if window_low > 0 and prices[i] <= window_low * (1 + dip):
            entry = prices[i]
            exit_idx = i + hold_days
            exit_price = prices[exit_idx]
            ret = (exit_price - entry) / entry
            trades.append({
                "entry_date": dates[i], "entry": round(entry, 4),
                "exit_date": dates[exit_idx], "exit": round(exit_price, 4),
                "return_pct": round(ret * 100, 2),
            })
            i = exit_idx + 1  # non-overlapping
        else:
            i += 1

    wins = [t for t in trades if t["return_pct"] > 0]
    # Compounded strategy return across sequential trades.
    strat_growth = 1.0
    for t in trades:
        strat_growth *= (1 + t["return_pct"] / 100.0)
    buy_hold = (prices[-1] - prices[0]) / prices[0] if prices[0] else 0.0
    avg_ret = (sum(t["return_pct"] for t in trades) / len(trades)) if trades else 0.0

    return {
        "ticker": ticker,
        "ok": True,
        "params": {"period": period, "lookback": lookback, "dip": dip, "hold_days": hold_days},
        "bars": n,
        "start_date": dates[0],
        "end_date": dates[-1],
        "num_trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0.0,
        "avg_return_pct": round(avg_ret, 2),
        "strategy_return_pct": round((strat_growth - 1) * 100, 2),
        "buy_hold_return_pct": round(buy_hold * 100, 2),
        "trades": trades[-50:],
    }

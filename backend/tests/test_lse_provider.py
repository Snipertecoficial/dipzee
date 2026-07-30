"""Unit tests for LSEProvider — London Strategic Edge as the primary source.

Everything runs offline: the LSE SDK client is replaced by a fake exposing the
real 0.14.0 shapes (``candles`` -> oldest-first list of OHLCV dicts;
``fundamentals`` -> single-element list of a company snapshot). We assert the
normalized quote, the empty-coverage / over-budget fall-throughs, and that the
cascade puts ``lse`` first (with automatic fallback to the next provider).
"""
import providers
import lse_service


class _FakeClient:
    """Mimics the lse-data SDK: candles (oldest-first) + fundamentals (list of 1)."""

    def __init__(self, candles=None, fundamentals=None):
        self._candles = candles
        self._fundamentals = fundamentals
        self.candle_calls = 0
        self.fund_calls = 0

    def candles(self, symbol, timeframe, start=None, end=None, limit=None):
        self.candle_calls += 1
        return self._candles

    def fundamentals(self, symbol):
        self.fund_calls += 1
        return self._fundamentals


def _series(prices):
    """Oldest-first daily candles from a list of closes (high/low bracket each)."""
    return [
        {"symbol": "T", "open": p, "high": p + 1, "low": p - 1, "close": p,
         "volume": 1000, "timestamp": f"2026-01-{i + 1:02d}T00:00:00.000000Z"}
        for i, p in enumerate(prices)
    ]


_FUND = [{
    "symbol": "NVDA", "name": "NVIDIA Corporation", "exchange": "NASDAQ",
    "currency": "USD", "sector": "Technology", "dividend_yield": 0.0002,
    "logo_url": "https://api.londonstrategicedge.com/logos/NVDA.png",
    "current_price": 188.63, "week_52_high": 212.19, "week_52_low": 86.62,
}]


def _wire(monkeypatch, client, *, configured=True, budget=True):
    monkeypatch.setattr(lse_service, "is_configured", lambda: configured)
    monkeypatch.setattr(lse_service, "under_local_budget", lambda: budget)
    monkeypatch.setattr(lse_service, "record_call", lambda: None)
    monkeypatch.setattr(lse_service, "_get_client", lambda: client)
    # Fundamentals are cached per-symbol on the class; keep tests isolated.
    providers.LSEProvider._fund_cache.clear()


# --- fetch: happy path ------------------------------------------------------ #

def test_fetch_normalizes_candles_and_fundamentals(monkeypatch):
    client = _FakeClient(candles=_series([100, 102, 105, 101, 108]), fundamentals=_FUND)
    _wire(monkeypatch, client)

    d = providers.LSEProvider().fetch("NVDA")

    assert d is not None
    assert d["source"] == "lse"
    assert d["price"] == 108            # last close
    assert d["prev_close"] == 101       # second-to-last close
    assert d["high_52w"] == 109         # max high (108 + 1)
    assert d["low_52w"] == 99           # min low (100 - 1)
    # change_pct = (108 - 101) / 101 * 100
    assert round(d["change_pct"], 2) == 6.93
    assert d["name"] == "NVIDIA Corporation"
    assert d["exchange"] == "NASDAQ"
    assert d["currency"] == "USD"
    assert d["sector"] == "Technology"
    assert d["logo"].endswith("/NVDA.png")
    assert d["dividend_yield"] == 0.0002   # already a decimal fraction, kept
    assert d["target_mean"] is None        # LSE has no consensus -> backfilled later


def test_fetch_uses_live_candles_not_stale_snapshot(monkeypatch):
    # fundamentals carry a stale 52w range; candles must win for the range/price.
    client = _FakeClient(candles=_series([150, 160, 170]), fundamentals=_FUND)
    _wire(monkeypatch, client)
    d = providers.LSEProvider().fetch("NVDA")
    assert d["price"] == 170
    assert d["high_52w"] == 171          # from candles, not fundamentals' 212.19
    assert d["low_52w"] == 149


def test_fetch_dividend_yield_is_clamped(monkeypatch):
    # A mis-scaled 250 (=25000%) must never leak; the shared clamp rescales it.
    fund = [dict(_FUND[0], dividend_yield=250)]
    client = _FakeClient(candles=_series([10, 11]), fundamentals=fund)
    _wire(monkeypatch, client)
    d = providers.LSEProvider().fetch("NVDA")
    assert 0 <= d["dividend_yield"] <= 0.30


# --- fetch: fall-through cases (return None -> cascade continues) ------------ #

def test_fetch_empty_candles_returns_none(monkeypatch):
    client = _FakeClient(candles=[], fundamentals=_FUND)
    _wire(monkeypatch, client)
    assert providers.LSEProvider().fetch("ENB.TO") is None


def test_fetch_over_budget_returns_none_without_calling_sdk(monkeypatch):
    client = _FakeClient(candles=_series([1, 2, 3]), fundamentals=_FUND)
    _wire(monkeypatch, client, budget=False)
    assert providers.LSEProvider().fetch("NVDA") is None
    assert client.candle_calls == 0      # budget guard short-circuits before any call


def test_fetch_not_configured_returns_none(monkeypatch):
    client = _FakeClient(candles=_series([1, 2, 3]), fundamentals=_FUND)
    _wire(monkeypatch, client, configured=False)
    assert providers.LSEProvider().fetch("NVDA") is None


def test_fetch_survives_fundamentals_failure(monkeypatch):
    class _Boom(_FakeClient):
        def fundamentals(self, symbol):
            raise RuntimeError("fundamentals 500")

    client = _Boom(candles=_series([50, 51, 52]))
    _wire(monkeypatch, client)
    d = providers.LSEProvider().fetch("NVDA")
    assert d is not None and d["price"] == 52
    assert d["name"] == "NVDA"           # falls back to the symbol
    assert d["sector"] is None


# --- fundamentals caching --------------------------------------------------- #

def test_fundamentals_cached_across_fetches(monkeypatch):
    client = _FakeClient(candles=_series([10, 11, 12]), fundamentals=_FUND)
    _wire(monkeypatch, client)
    prov = providers.LSEProvider()
    prov.fetch("NVDA")
    prov.fetch("NVDA")
    assert client.candle_calls == 2      # live price re-fetched every time
    assert client.fund_calls == 1        # static facts pulled once, then cached


# --- cascade wiring --------------------------------------------------------- #

def test_quote_chain_puts_lse_first_when_configured(monkeypatch):
    monkeypatch.setattr(lse_service, "is_configured", lambda: True)
    monkeypatch.delenv("PRIMARY_PROVIDER", raising=False)
    chain = [getattr(p, "name", None) for p in providers._quote_chain()]
    assert chain[0] == "lse"


def test_quote_chain_omits_lse_when_not_configured(monkeypatch):
    monkeypatch.setattr(lse_service, "is_configured", lambda: False)
    monkeypatch.delenv("PRIMARY_PROVIDER", raising=False)
    chain = [getattr(p, "name", None) for p in providers._quote_chain()]
    assert "lse" not in chain


def test_quote_chain_respects_explicit_other_primary(monkeypatch):
    monkeypatch.setattr(lse_service, "is_configured", lambda: True)
    monkeypatch.setenv("PRIMARY_PROVIDER", "investing")
    chain = [getattr(p, "name", None) for p in providers._quote_chain()]
    assert "lse" not in chain            # explicit non-LSE primary opts LSE out


def test_fetch_resilient_falls_through_when_lse_returns_none(monkeypatch):
    # LSE first but uncovered -> next provider in the chain serves the quote.
    class _NullLSE(providers.LSEProvider):
        def fetch(self, symbol):
            return None

    class _Stub(providers.DataProvider):
        name = "stub"

        def fetch(self, symbol):
            return {"ticker": symbol, "price": 42.0}

        def search(self, query):
            return []

    monkeypatch.setattr(providers, "_quote_chain", lambda: [_NullLSE(), _Stub()])
    d = providers.fetch_resilient("NVDA")
    assert d["price"] == 42.0
    assert d["source"] == "stub"

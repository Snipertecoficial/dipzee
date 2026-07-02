# Here are your Instructions


## Market Data Layer (/api/market/*)

Resilient market-data service built on **Finnhub (primary quote) + yfinance**, with an in-memory TTL cache, durable MongoDB snapshots (`market_cache` collection) and a **stale-on-error fallback**: when the upstream (Yahoo/Finnhub) is rate-limited or down, the last-known-good value is served (`stale: true`) instead of an error. A hard `502` is only returned when no data ever existed.

### Endpoints
- `GET /api/market/health`
- `GET /api/market/quote/{symbol}` (TTL 15s)
- `GET /api/market/history/{symbol}?period=1mo&interval=1d` (TTL 1h)
- `GET /api/market/batch?symbols=AAPL,MSFT&period=1mo` (TTL 15m)
- `GET /api/market/summary/{market}` e.g. `US`, `GB` (TTL 5m)
- `GET /api/market/search?q=apple` (quotes + news, TTL 5m)
- `GET /api/market/fundamentals/{symbol}` (income/balance/cashflow/calendar/targets, TTL 24h)
- `GET /api/market/options/{symbol}?expiration=YYYY-MM-DD` (TTL 1h)
- `GET /api/market/screener?type=day_gainers&count=25` (TTL 5m)

All responses use the envelope `{ ok, data, cached, stale, fetched_at }`.

### Honesty / production note
yfinance uses Yahoo's public/undocumented endpoints and is intended for personal/research use. Aggressive caching + backoff + stale fallback make it robust, but there is **no legitimate way to guarantee zero rate-limiting** on Yahoo. For a commercial production SaaS, swap the loaders in `market_service.py` for a **licensed provider** (FMP / Finnhub paid / Polygon.io / Twelve Data / Alpha Vantage) — the cache/router layers stay identical, so only the service layer changes.

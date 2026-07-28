"""Curated domain knowledge for the financial knowledge graph (L1).

Kept separate from the graph *logic* (``knowledge_graph.py``) so the two evolve
independently: this file is data — defensible economic priors about how sectors
react to macro factors and commodities. Signs and weights are heuristics
(clearly first-order, not a factor model), used to rank *which assets an event
plausibly touches* — never as advice.

Sector names use the provider taxonomy (yfinance/FMP). ``normalize_sector``
folds the common aliases so company sectors from any provider line up with the
edges defined here.
"""

# Canonical sectors (provider taxonomy) -> display name.
SECTORS = {
    "Technology": "Technology",
    "Communication Services": "Communication Services",
    "Financial Services": "Financial Services",
    "Healthcare": "Healthcare",
    "Consumer Cyclical": "Consumer Cyclical",
    "Consumer Defensive": "Consumer Defensive",
    "Energy": "Energy",
    "Industrials": "Industrials",
    "Utilities": "Utilities",
    "Real Estate": "Real Estate",
    "Basic Materials": "Basic Materials",
}

# Fold common provider aliases into the canonical names above.
_SECTOR_ALIASES = {
    "materials": "Basic Materials",
    "basic materials": "Basic Materials",
    "financials": "Financial Services",
    "financial": "Financial Services",
    "financial services": "Financial Services",
    "information technology": "Technology",
    "tech": "Technology",
    "communication": "Communication Services",
    "telecommunication services": "Communication Services",
    "health care": "Healthcare",
    "consumer discretionary": "Consumer Cyclical",
    "consumer staples": "Consumer Defensive",
    "real estate": "Real Estate",
    "utilities": "Utilities",
    "energy": "Energy",
    "industrials": "Industrials",
}


def normalize_sector(sector: str):
    """Canonical sector name for any provider spelling, or None if unknown."""
    if not sector:
        return None
    s = str(sector).strip()
    if s in SECTORS:
        return s
    return _SECTOR_ALIASES.get(s.lower())


# Commodity -> {display, sectors: {sector: weight}}. Weight is exposure
# magnitude; sign is +1 (a rise in the commodity helps the sector). Negatives
# below encode input-cost drag.
COMMODITY_EXPOSURE = {
    "crude_oil": {"name": "Crude Oil", "sectors": {
        "Energy": 0.90, "Industrials": -0.30, "Consumer Cyclical": -0.40, "Utilities": -0.20,
    }},
    "natural_gas": {"name": "Natural Gas", "sectors": {
        "Energy": 0.70, "Utilities": -0.40, "Basic Materials": -0.30,
    }},
    "gold": {"name": "Gold", "sectors": {
        "Basic Materials": 0.55,
    }},
    "copper": {"name": "Copper", "sectors": {
        "Basic Materials": 0.60, "Industrials": 0.20,
    }},
    "agriculture": {"name": "Agricultural Commodities", "sectors": {
        "Consumer Defensive": -0.30, "Basic Materials": 0.30,
    }},
}

# Macro factor -> {display, sectors: {sector: (weight, sign)}}. Sign is how the
# sector reacts to a RISE in the factor: +1 benefits, -1 hurt.
MACRO_SENSITIVITY = {
    "interest_rates": {"name": "Interest Rates", "sectors": {
        "Financial Services": (0.60, +1),
        "Real Estate": (0.80, -1),
        "Utilities": (0.70, -1),
        "Technology": (0.50, -1),
        "Consumer Cyclical": (0.40, -1),
    }},
    "inflation": {"name": "Inflation", "sectors": {
        "Energy": (0.50, +1),
        "Basic Materials": (0.50, +1),
        "Consumer Defensive": (0.20, +1),
        "Technology": (0.30, -1),
        "Consumer Cyclical": (0.40, -1),
    }},
    "usd": {"name": "US Dollar", "sectors": {
        "Basic Materials": (0.40, -1),
        "Energy": (0.30, -1),
        "Technology": (0.30, -1),
        "Industrials": (0.30, -1),
    }},
    "unemployment": {"name": "Unemployment", "sectors": {
        "Consumer Cyclical": (0.50, -1),
        "Financial Services": (0.30, -1),
        "Consumer Defensive": (0.20, +1),
    }},
}

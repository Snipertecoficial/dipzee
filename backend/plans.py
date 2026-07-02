"""Per-plan limits and capability matrix (single source of truth for gating)."""

# Numeric limits (None = unlimited).
PLAN_LIMITS = {
    "none": {"watchlist": 0, "alerts": 0, "locales": ["en", "fr", "pt", "es"], "intraday": False},
    "starter": {"watchlist": 25, "alerts": 10, "locales": ["en", "fr", "pt", "es"], "intraday": False},
    "pro": {"watchlist": None, "alerts": None, "locales": ["en", "fr", "pt", "es"], "intraday": False},
    "investor": {"watchlist": None, "alerts": None, "locales": ["en", "fr", "pt", "es"], "intraday": True},
}

# Capability flags per plan (feature gating). Higher tiers inherit lower ones.
PLAN_FEATURES = {
    "none": [],
    "starter": [
        "search", "watchlist", "alerts", "email_alerts", "in_app_alerts",
        "eod_data", "all_locales",
    ],
    "pro": [
        "search", "watchlist", "alerts", "email_alerts", "in_app_alerts",
        "all_locales", "dividend_tracker", "screener", "charts", "fundamentals",
        "options",
    ],
    "investor": [
        "search", "watchlist", "alerts", "email_alerts", "in_app_alerts",
        "all_locales", "dividend_tracker", "screener", "charts", "fundamentals",
        "options", "intraday", "advanced_screener", "portfolio", "backtest",
        "messaging_alerts", "export", "priority",
    ],
}

PLAN_RANK = {"none": 0, "starter": 1, "pro": 2, "investor": 3}

# Plans that grant access to the product (an active/trialing subscription).
PAID_PLANS = {"starter", "pro", "investor"}

# i18n keys of the marketing bullet list shown on the pricing cards (kept in
# lockstep with the real capabilities above so we never overpromise).
PLAN_CARD_FEATURES = {
    "starter": ["starterF1", "starterF2", "starterF3", "starterF4", "starterF5"],
    "pro": ["proF1", "proF2", "proF3", "proF4", "proF5", "proF6"],
    "investor": ["investorF1", "investorF2", "investorF3", "investorF4", "investorF5", "investorF6", "investorF7"],
}


def limit_for(plan: str, key: str):
    return PLAN_LIMITS.get(plan or "none", PLAN_LIMITS["none"]).get(key)


def has_access(plan: str) -> bool:
    return (plan or "none") in PAID_PLANS


def has_feature(plan: str, feature: str) -> bool:
    return feature in PLAN_FEATURES.get(plan or "none", [])


def plan_rank(plan: str) -> int:
    return PLAN_RANK.get(plan or "none", 0)


def plan_capabilities(plan: str) -> dict:
    """Everything the frontend needs to render UI + gate features for a plan."""
    plan = plan if plan in PLAN_FEATURES else "none"
    return {
        "plan": plan,
        "rank": plan_rank(plan),
        "limits": PLAN_LIMITS.get(plan, PLAN_LIMITS["none"]),
        "features": PLAN_FEATURES.get(plan, []),
    }


def catalog() -> dict:
    """Public catalog (limits + features + card bullet keys) for all paid plans."""
    out = {}
    for plan in ("starter", "pro", "investor"):
        out[plan] = {
            "rank": PLAN_RANK[plan],
            "limits": PLAN_LIMITS[plan],
            "features": PLAN_FEATURES[plan],
            "card_features": PLAN_CARD_FEATURES[plan],
        }
    return out

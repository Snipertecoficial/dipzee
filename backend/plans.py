"""Per-plan feature limits (enforced via helpers / middleware)."""

PLAN_LIMITS = {
    "none": {"watchlist": 0, "alerts": 0, "locales": ["en", "fr", "pt", "es"], "intraday": False},
    "starter": {"watchlist": 25, "alerts": 10, "locales": ["en", "fr", "pt", "es"], "intraday": False},
    "pro": {"watchlist": None, "alerts": None, "locales": ["en", "fr", "pt", "es"], "intraday": False},
    "investor": {"watchlist": None, "alerts": None, "locales": ["en", "fr", "pt", "es"], "intraday": True},
}


def limit_for(plan: str, key: str):
    return PLAN_LIMITS.get(plan or "none", PLAN_LIMITS["none"]).get(key)


# Plans that grant access to the product (an active/trialing subscription).
PAID_PLANS = {"starter", "pro", "investor"}


def has_access(plan: str) -> bool:
    return (plan or "none") in PAID_PLANS

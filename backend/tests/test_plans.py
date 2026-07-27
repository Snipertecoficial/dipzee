"""Unit tests for plan gating — the single source of truth for who can do what."""
from plans import has_feature, limit_for, plan_rank, has_access, plan_capabilities


def test_feature_gating_by_plan():
    # A paid-only feature is denied on lower tiers and granted on the right one.
    assert has_feature("investor", "messaging_alerts") is True
    assert has_feature("pro", "messaging_alerts") is False   # Investor-only
    assert has_feature("pro", "ai_analyst") is True
    assert has_feature("starter", "ai_analyst") is False
    assert has_feature("none", "search") is False
    assert has_feature(None, "search") is False  # None normalizes to "none"


def test_alert_limits():
    assert limit_for("none", "alerts") == 0
    assert limit_for("starter", "alerts") == 10
    assert limit_for("pro", "alerts") is None      # unlimited
    assert limit_for("investor", "alerts") is None


def test_plan_rank_ordering():
    assert plan_rank("none") < plan_rank("starter") < plan_rank("pro") < plan_rank("investor")
    assert plan_rank("bogus") == 0


def test_has_access():
    assert has_access("starter") is True
    assert has_access("none") is False
    assert has_access(None) is False


def test_capabilities_normalizes_unknown_plan():
    cap = plan_capabilities("not-a-plan")
    assert cap["plan"] == "none"
    assert cap["features"] == []
    inv = plan_capabilities("investor")
    assert inv["rank"] == 3 and "backtest" in inv["features"]

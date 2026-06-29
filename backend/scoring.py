"""Pure, unit-tested Opportunity Score engine for Dipzee.

The score combines three sub-scores (buy, upside, income). Weights and
thresholds are configurable through the SETTINGS object so the product team
can tune the model without touching the math.
"""
from typing import Optional

# Configurable settings object (weights + thresholds)
SETTINGS = {
    "weights": {"buy": 0.45, "upside": 0.35, "income": 0.20},
    "upside": {"target_weight": 0.6, "high_weight": 0.4, "cap": 0.60},
    "income": {"cap": 0.06},
    "flags": {"buy_zone_r": 0.15, "sell_zone_r": 0.85, "income_d": 0.04},
    # ordered high -> low
    "classification": [
        (80, "strong_buy"),
        (65, "buy"),
        (45, "hold"),
        (30, "reduce"),
        (0, "sell"),
    ],
}


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def classify(score: int, settings: dict = SETTINGS) -> str:
    for threshold, label in settings["classification"]:
        if score >= threshold:
            return label
    return "sell"


def compute_opportunity_score(
    P: Optional[float],
    L: Optional[float],
    H: Optional[float],
    T: Optional[float],
    D: Optional[float],
    settings: dict = SETTINGS,
) -> Optional[dict]:
    """Compute the 0-100 Opportunity Score.

    P = price, L = 52w low, H = 52w high, T = analyst target, D = dividend yield (decimal).
    Returns None when there is not enough data to score.
    """
    w = settings["weights"]
    up = settings["upside"]
    inc = settings["income"]
    fl = settings["flags"]

    if P is None or L is None or H is None or H == L:
        return None

    P = float(P)
    L = float(L)
    H = float(H)
    D = float(D) if D is not None else 0.0

    R = _clamp((P - L) / (H - L), 0.0, 1.0)

    upside_high = (H - P) / P if P > 0 else 0.0
    has_target = T is not None and float(T) > 0
    if has_target:
        upside_target = (float(T) - P) / P if P > 0 else 0.0
        U = up["target_weight"] * upside_target + up["high_weight"] * upside_high
    else:
        upside_target = None
        U = upside_high

    S_buy = (1 - R) * 100
    S_up = _clamp(U / up["cap"], 0.0, 1.0) * 100
    S_div = _clamp(D / inc["cap"], 0.0, 1.0) * 100

    score = round(w["buy"] * S_buy + w["upside"] * S_up + w["income"] * S_div)
    classification = classify(score, settings)

    flags = {
        "buy_zone": R <= fl["buy_zone_r"],
        "sell_zone": (R >= fl["sell_zone_r"]) or (has_target and P >= float(T)),
        "income": D >= fl["income_d"],
    }

    return {
        "score": int(score),
        "sub_scores": {
            "buy": round(S_buy, 2),
            "upside": round(S_up, 2),
            "income": round(S_div, 2),
        },
        "classification": classification,
        "flags": flags,
        "R": round(R, 4),
        "U": round(U, 4),
        "upside_target": round(upside_target, 4) if upside_target is not None else None,
        "upside_high": round(upside_high, 4),
    }

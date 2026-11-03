"""Deterministic verdict rules (pre-registered in PREREG.md)."""
from __future__ import annotations

FAST_GAIN_MIN = 0.01          # < 1 point gain -> fast mode
OVERTHINK_RATE = 0.03         # right->wrong >= 3% of items
OVERTHINK_SHARE = 0.30        # or >= 30% of all flips
CONF_COVERAGE_MIN = 0.30      # safe threshold must cover >= 30% of items


def mode_choice(diff: dict, cost_gut_1k: float, cost_rea_1k: float, n_items: int) -> dict:
    lo, hi = diff["ci"]
    if (lo <= 0 <= hi) or diff["diff"] < FAST_GAIN_MIN:
        why = "accuracy gain CI includes 0" if lo <= 0 <= hi else "gain < 1 point"
        return {"verdict": "Use fast mode", "why": why}
    extra_correct_per_1k = diff["diff"] * 1000
    cpec = (cost_rea_1k - cost_gut_1k) / extra_correct_per_1k if extra_correct_per_1k > 0 else None
    return {"verdict": "Use reasoning", "why": f"+{diff['diff'] * 100:.1f} pts, CI excludes 0",
            "cost_per_extra_correct_usd": cpec}


def overthinking(fl: dict) -> bool:
    return fl["overthinking_rate"] >= OVERTHINK_RATE or (
        fl["flips"] > 0 and fl["overthinking_share_of_flips"] >= OVERTHINK_SHARE)


def confidence_usable(th: dict) -> bool:
    return bool(th.get("found")) and th["coverage"] >= CONF_COVERAGE_MIN


def cheapest(configs: list[dict], target_acc: float) -> dict:
    """configs: [{model, mode, cost_per_1k, acc_ci_lo, threshold: {...}}]."""
    by_acc = sorted([c for c in configs if c["acc_ci_lo"] >= target_acc], key=lambda c: c["cost_per_1k"])
    by_auto = sorted([c for c in configs if confidence_usable(c["threshold"])],
                     key=lambda c: (-c["threshold"]["coverage"], c["cost_per_1k"]))
    return {
        "by_accuracy": ({"model": by_acc[0]["model"], "mode": by_acc[0]["mode"],
                         "cost_per_1k": by_acc[0]["cost_per_1k"]} if by_acc else None),
        "by_auto_accept": ({"model": by_auto[0]["model"], "mode": by_auto[0]["mode"],
                            "cost_per_1k": by_auto[0]["cost_per_1k"],
                            "coverage": by_auto[0]["threshold"]["coverage"],
                            "threshold": by_auto[0]["threshold"]["threshold"]} if by_auto else None),
    }

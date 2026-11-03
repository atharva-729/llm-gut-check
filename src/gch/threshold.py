"""Safe auto-accept threshold: lowest confidence t whose Wilson lower bound on precision >= target."""
from __future__ import annotations

import math

Z95 = 1.959963984540054


def wilson_lower(k: int, n: int, z: float = Z95) -> float:
    if n == 0:
        return 0.0
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - margin) / denom


def search(rows: list[dict], target: float, min_n: int = 30) -> dict:
    """rows: all items for one task x model x mode. Parse failures are never auto-accepted
    but count in the coverage denominator."""
    total = len(rows)
    ok = [r for r in rows if r.get("status") == "ok" and r.get("confidence") is not None]
    for t in sorted({r["confidence"] for r in ok}):
        above = [r for r in ok if r["confidence"] >= t]
        n = len(above)
        if n < min_n:
            break  # higher thresholds only shrink n
        k = sum(1 for r in above if r.get("correct"))
        lb = wilson_lower(k, n)
        if lb >= target:
            return {"target": target, "threshold": t, "n_above": n, "precision": k / n,
                    "precision_lower": lb, "coverage": n / total if total else 0.0, "found": True}
    return {"target": target, "threshold": None, "found": False,
            "min_all_correct_n_needed": min_all_correct_n(target)}


def min_all_correct_n(target: float) -> int:
    """Smallest n such that n/n correct passes the Wilson bound — the floor on sample size."""
    n = 1
    while wilson_lower(n, n) < target:
        n += 1
    return n

"""v1.1 confirmation study: auto-accept policies (SELF / AGREE / MAJ) fitted on discovery, tested on confirmation.

Everything here is pre-registered in PREREG.md (Addendum v1.1).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations

import numpy as np

from .threshold import wilson_lower

CONF_GRID = [0, 50, 60, 70, 80, 85, 90, 95, 100]
FIT_PRECISION = 0.97
TARGET = 0.95
MIN_N = 30
R_REVIEW = 0.25
E_ERROR = 2.50
SENS_R = [0.05, 0.25, 1.00]
SENS_E = [0.0, 2.50, 25.0]


# ---------------------------------------------------------------- data shaping
def index(results: list[dict]) -> dict:
    """task -> item_id -> (model, mode) -> row"""
    d = defaultdict(lambda: defaultdict(dict))
    for r in results:
        d[r["task"]][r["item_id"]][(r["model"], r["mode"])] = r
    return d


def _ok(row: dict | None) -> bool:
    return bool(row) and row.get("status") == "ok" and row.get("confidence") is not None


# ---------------------------------------------------------------- policies
def make_policies(models: list[str]) -> list[dict]:
    pols = []
    for m in models:
        for mode in ("gut", "reasoned"):
            pols.append({"kind": "SELF", "models": (m,), "mode": mode})
    for mode in ("gut", "reasoned"):
        for k in (2, 3):
            for s in combinations(models, k):
                pols.append({"kind": "AGREE", "models": tuple(s), "mode": mode})
        if len(models) >= 3:
            pols.append({"kind": "MAJ", "models": tuple(models), "mode": mode})
    return pols


def name(p: dict) -> str:
    short = {"gpt-5.4-mini": "gpt", "claude-haiku-4-5": "haiku", "gemini-3.5-flash": "gemini"}
    ms = "+".join(short.get(m, m) for m in p["models"])
    return f"{p['kind']}({ms}, {p['mode']})"


def decide(p: dict, cells: dict, c: float) -> str | None:
    """Return the accepted answer, or None if the item goes to review."""
    rows = [cells.get((m, p["mode"])) for m in p["models"]]
    if p["kind"] in ("SELF", "AGREE"):
        if not all(_ok(r) for r in rows):
            return None
        answers = {r["answer"] for r in rows}
        if len(answers) == 1 and all(r["confidence"] >= c for r in rows):
            return rows[0]["answer"]
        return None
    if p["kind"] == "MAJ":
        ok = [r for r in rows if _ok(r)]
        if not ok:
            return None
        ans, n = Counter(r["answer"] for r in ok).most_common(1)[0]
        if n < 2:
            return None
        agreeing = [r for r in ok if r["answer"] == ans]
        return ans if all(r["confidence"] >= c for r in agreeing) else None
    raise ValueError(p["kind"])


def evaluate(p: dict, items: dict, c: float) -> dict:
    n_total = len(items)
    acc = cor = 0
    cost = 0.0
    for cells in items.values():
        cost += sum((cells.get((m, p["mode"])) or {}).get("cost_usd", 0.0) for m in p["models"])
        a = decide(p, cells, c)
        if a is not None:
            acc += 1
            gold = next(iter(cells.values()))["gold"]
            cor += a == gold
    return {
        "c": c, "n_total": n_total, "accepted": acc, "correct": cor,
        "precision": cor / acc if acc else float("nan"),
        "precision_lower": wilson_lower(cor, acc) if acc else 0.0,
        "coverage": acc / n_total if n_total else 0.0,
        "api_cost_per_1k": cost / n_total * 1000 if n_total else float("nan"),
    }


def fit(p: dict, disc_items: dict) -> float | None:
    for c in CONF_GRID:
        e = evaluate(p, disc_items, c)
        if e["accepted"] >= MIN_N and e["precision"] >= FIT_PRECISION:
            return c
    return None


def total_cost_per_1k(e: dict, R: float = R_REVIEW, E: float = E_ERROR) -> float:
    n = e["n_total"]
    wrong = e["accepted"] - e["correct"]
    return e["api_cost_per_1k"] + (R * (n - e["accepted"]) + E * wrong) / n * 1000


def passes(e: dict) -> bool:
    return e["accepted"] >= MIN_N and e["precision_lower"] >= TARGET


def run_policies(disc: dict, conf: dict, models: list[str]) -> list[dict]:
    """disc/conf: item_id -> cells for ONE task."""
    out = []
    for p in make_policies(models):
        c = fit(p, disc)
        row = {"policy": name(p), **p, "models": list(p["models"]), "fitted_c": c}
        if c is None:
            row.update({"fitted": False, "passes": False})
        else:
            e = evaluate(p, conf, c)
            row.update({"fitted": True, **e, "passes": passes(e),
                        "total_cost_per_1k": total_cost_per_1k(e),
                        "sensitivity": {f"R={R},E={E}": total_cost_per_1k(e, R, E) for R in SENS_R for E in SENS_E}})
        # no-automation baseline API cost is still useful context
        row["discovery_at_fit"] = evaluate(p, disc, c) if c is not None else None
        out.append(row)
    return out


def h4(pol_rows: list[dict]) -> dict:
    passing = [r for r in pol_rows if r.get("passes")]
    selfs = [r for r in passing if r["kind"] == "SELF"]
    agrees = [r for r in passing if r["kind"] in ("AGREE", "MAJ") and r["mode"] == "gut"]
    best_self = max(selfs, key=lambda r: (r["coverage"], -r["api_cost_per_1k"]), default=None)
    best_agree = max(agrees, key=lambda r: (r["coverage"], -r["api_cost_per_1k"]), default=None)
    self_cov = best_self["coverage"] if best_self else 0.0
    self_cost = best_self["api_cost_per_1k"] if best_self else float("inf")
    holds = bool(best_agree) and best_agree["coverage"] >= self_cov and best_agree["api_cost_per_1k"] < self_cost
    return {"best_self": best_self and best_self["policy"], "best_self_coverage": self_cov,
            "best_self_cost": None if not best_self else self_cost,
            "best_gut_agree": best_agree and best_agree["policy"],
            "best_gut_agree_coverage": best_agree["coverage"] if best_agree else 0.0,
            "best_gut_agree_cost": best_agree["api_cost_per_1k"] if best_agree else None,
            "holds": holds}


# ---------------------------------------------------------------- H5: ambiguity blindness (toxicity)
def _boot_diff(a: np.ndarray, b: np.ndarray, seed: int = 20261104, n: int = 2000) -> tuple[float, list[float]]:
    rng = np.random.default_rng(seed)
    d = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(n)]
    return float(a.mean() - b.mean()), [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]


def h5(items: dict, items_meta: dict, models: list[str]) -> dict:
    out = {}
    for m in models:
        split_acc, clear_acc, split_conf, clear_conf = [], [], [], []
        for iid, cells in items.items():
            r = cells.get((m, "gut"))
            if not r:
                continue
            score = items_meta[iid]["meta"]["toxicity"]
            is_split = 0.3 <= score <= 0.7
            (split_acc if is_split else clear_acc).append(1.0 if r.get("correct") else 0.0)
            if _ok(r):
                (split_conf if is_split else clear_conf).append(r["confidence"])
        da, ca = _boot_diff(np.array(split_acc), np.array(clear_acc))
        dc, cc = _boot_diff(np.array(split_conf), np.array(clear_conf))
        out[m] = {"n_split": len(split_acc), "n_clear": len(clear_acc),
                  "acc_split": float(np.mean(split_acc)), "acc_clear": float(np.mean(clear_acc)),
                  "acc_diff": da, "acc_diff_ci": ca,
                  "conf_split": float(np.mean(split_conf)), "conf_clear": float(np.mean(clear_conf)),
                  "conf_diff": dc, "conf_diff_ci": cc,
                  "holds": ca[1] < 0 and cc[1] >= 0}
    n_hold = sum(v["holds"] for v in out.values())
    return {"per_model": out, "supported": n_hold >= 2, "n_models_holding": n_hold}


# ---------------------------------------------------------------- H6
def h6(items: dict, models: list[str], pol_rows: list[dict]) -> dict:
    agree = cor = 0
    for cells in items.values():
        rows = [cells.get((m, "gut")) for m in models]
        if all(_ok(r) for r in rows) and len({r["answer"] for r in rows}) == 1:
            agree += 1
            cor += rows[0]["answer"] == rows[0]["gold"]
    prec = cor / agree if agree else float("nan")
    any_pass = any(r.get("passes") for r in pol_rows)
    return {"unanimous_gut_items": agree, "unanimous_share": agree / len(items),
            "precision_when_unanimous": prec, "precision_lower": wilson_lower(cor, agree),
            "any_policy_passes": any_pass, "supported": prec < 0.85 and not any_pass}

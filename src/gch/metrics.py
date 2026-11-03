"""Accuracy (bootstrap CI), calibration (ECE, overconfidence), flips, cost and latency."""
from __future__ import annotations

import numpy as np

N_BOOT = 2000


def _rng(seed: int = 20261103) -> np.random.Generator:
    return np.random.default_rng(seed)


def correct_vector(rows: list[dict]) -> np.ndarray:
    """Primary analysis: parse failures count as incorrect."""
    return np.array([1.0 if r.get("correct") else 0.0 for r in rows])


def bootstrap_ci(x: np.ndarray, n_boot: int = N_BOOT, seed: int = 20261103) -> tuple[float, float]:
    if len(x) == 0:
        return (float("nan"), float("nan"))
    idx = _rng(seed).integers(0, len(x), size=(n_boot, len(x)))
    means = x[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def accuracy(rows: list[dict]) -> dict:
    x = correct_vector(rows)
    lo, hi = bootstrap_ci(x)
    return {"n": len(x), "acc": float(x.mean()) if len(x) else float("nan"), "ci": [lo, hi]}


def paired_diff(gut: dict[str, dict], rea: dict[str, dict]) -> dict:
    """Reasoned minus gut accuracy on items present in both, paired bootstrap CI."""
    ids = sorted(set(gut) & set(rea))
    g = np.array([1.0 if gut[i].get("correct") else 0.0 for i in ids])
    r = np.array([1.0 if rea[i].get("correct") else 0.0 for i in ids])
    d = r - g
    lo, hi = bootstrap_ci(d)
    return {"n": len(ids), "diff": float(d.mean()) if len(d) else float("nan"), "ci": [lo, hi]}


def ece(conf: np.ndarray, correct: np.ndarray, n_bins: int = 10) -> float:
    """Expected calibration error; conf in [0,1]. Bins are [0,.1), ..., [.9,1.0]."""
    if len(conf) == 0:
        return float("nan")
    bins = np.minimum((conf * n_bins).astype(int), n_bins - 1)
    total = 0.0
    for b in range(n_bins):
        m = bins == b
        if m.any():
            total += m.sum() / len(conf) * abs(conf[m].mean() - correct[m].mean())
    return float(total)


def reliability(conf: np.ndarray, correct: np.ndarray, n_bins: int = 10) -> list[dict]:
    bins = np.minimum((conf * n_bins).astype(int), n_bins - 1)
    out = []
    for b in range(n_bins):
        m = bins == b
        if m.any():
            out.append({"bin": b, "lo": b / n_bins, "hi": (b + 1) / n_bins, "n": int(m.sum()),
                        "mean_conf": float(conf[m].mean()), "acc": float(correct[m].mean())})
    return out


def calibration(rows: list[dict]) -> dict:
    ok = [r for r in rows if r.get("status") == "ok"]
    conf = np.array([r["confidence"] / 100 for r in ok])
    cor = np.array([1.0 if r["correct"] else 0.0 for r in ok])
    return {
        "n": len(ok),
        "ece": ece(conf, cor),
        "mean_conf": float(conf.mean()) if len(ok) else float("nan"),
        "acc_parsed": float(cor.mean()) if len(ok) else float("nan"),
        "overconfidence": float(conf.mean() - cor.mean()) if len(ok) else float("nan"),
        "reliability": reliability(conf, cor),
    }


def flips(gut: dict[str, dict], rea: dict[str, dict]) -> dict:
    ids = sorted(set(gut) & set(rea))
    c = {"right_to_wrong": 0, "wrong_to_right": 0, "wrong_to_wrong_changed": 0, "unchanged": 0}
    for i in ids:
        g, r = gut[i], rea[i]
        gc, rc = bool(g.get("correct")), bool(r.get("correct"))
        if gc and not rc:
            c["right_to_wrong"] += 1
        elif rc and not gc:
            c["wrong_to_right"] += 1
        elif not gc and not rc and g.get("answer") != r.get("answer"):
            c["wrong_to_wrong_changed"] += 1
        else:
            c["unchanged"] += 1
    n = len(ids)
    n_flips = c["right_to_wrong"] + c["wrong_to_right"] + c["wrong_to_wrong_changed"]
    return {**c, "n": n, "flips": n_flips,
            "overthinking_rate": c["right_to_wrong"] / n if n else float("nan"),
            "overthinking_share_of_flips": c["right_to_wrong"] / n_flips if n_flips else 0.0,
            "net_gain": c["wrong_to_right"] - c["right_to_wrong"]}


def cost_latency(rows: list[dict]) -> dict:
    cost = np.array([r.get("cost_usd", 0.0) for r in rows])
    lat = np.array([r["latency_s"] for r in rows if r.get("latency_s") is not None])
    reason = np.array([(r.get("usage") or {}).get("reasoning", 0) for r in rows])
    return {
        "cost_per_1k": float(cost.mean() * 1000) if len(cost) else float("nan"),
        "latency_median_s": float(np.median(lat)) if len(lat) else float("nan"),
        "latency_p90_s": float(np.percentile(lat, 90)) if len(lat) else float("nan"),
        "mean_reasoning_tokens": float(reason.mean()) if len(reason) else 0.0,
        "reasoning_leak_items": int((reason > 0).sum()),
    }

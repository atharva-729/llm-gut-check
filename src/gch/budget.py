"""Cost planner + soft budget + running spend log (runs/spend.json)."""
from __future__ import annotations

import json
import threading
from collections import defaultdict
from pathlib import Path

from .models import MODELS
from .tasks import load

ROOT = Path(__file__).resolve().parents[2]
SPEND = ROOT / "runs" / "spend.json"
_lock = threading.Lock()

# Prior per-call token guesses, replaced by pilot measurements when available.
PRIOR_OUT = {"gut": 30, "reasoned": {"gpt-5.4-mini": 800, "claude-haiku-4-5": 1100, "gemini-3.5-flash": 1000}}


def spent() -> float:
    if not SPEND.exists():
        return 0.0
    return float(json.loads(SPEND.read_text(encoding="utf-8")).get("total_usd", 0.0))


def add_spend(usd: float, split: str) -> None:
    if not usd:
        return
    with _lock:
        d = json.loads(SPEND.read_text(encoding="utf-8")) if SPEND.exists() else {"total_usd": 0.0, "by_split": {}}
        d["total_usd"] = d.get("total_usd", 0.0) + usd
        d["by_split"][split] = d["by_split"].get(split, 0.0) + usd
        SPEND.parent.mkdir(parents=True, exist_ok=True)
        SPEND.write_text(json.dumps(d, indent=2), encoding="utf-8")


def measured_per_call(results: list[dict]) -> dict:
    """Mean (input, output) tokens per call by (task, model, mode) from earlier results."""
    acc = defaultdict(lambda: [0, 0, 0])
    for r in results:
        u = r.get("usage") or {}
        if not u:
            continue
        k = (r["task"], r["model"], r["mode"])
        acc[k][0] += u.get("input", 0)
        acc[k][1] += u.get("output", 0)
        acc[k][2] += 1
    return {k: (a / n, b / n) for k, (a, b, n) in acc.items() if n}


def plan(jobs: list[dict], measured: dict | None = None, overhead: float = 0.15) -> dict:
    measured = measured or {}
    rows = defaultdict(lambda: {"calls": 0, "usd": 0.0, "source": "prior"})
    for j in jobs:
        m = MODELS[j["model"]]
        k = (j["task"], j["model"], j["mode"])
        if k in measured:
            tin, tout = measured[k]
            src = "pilot"
        else:
            tin = len(load(j["task"]).system_prompt) / 3.6 + 60
            tout = PRIOR_OUT["gut"] if j["mode"] == "gut" else PRIOR_OUT["reasoned"][j["model"]]
            src = "prior"
        row = rows[k]
        row["calls"] += 1
        row["usd"] += (tin * m.price_in + tout * m.price_out) / 1e6
        row["source"] = src
    total = sum(r["usd"] for r in rows.values()) * (1 + overhead)
    return {"rows": dict(rows), "total_usd": total}


def print_plan(p: dict, budget_usd: float) -> None:
    print(f"{'task':<11}{'model':<18}{'mode':<10}{'calls':>6}{'USD':>9}  basis")
    for (t, m, mode), r in sorted(p["rows"].items()):
        print(f"{t:<11}{m:<18}{mode:<10}{r['calls']:>6}{r['usd']:>9.3f}  {r['source']}")
    s = spent()
    print(f"\nEstimate (incl. retry overhead): ${p['total_usd']:.2f}   spent so far: ${s:.2f}   "
          f"budget: ${budget_usd:.2f}   remaining after run: ${budget_usd - s - p['total_usd']:.2f}")

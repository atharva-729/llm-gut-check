"""`gch site`: build docs/index.html (client demo) from reports/ + run logs. Every number on the page comes from here."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .tasks import load

ROOT = Path(__file__).resolve().parents[2]
TASKS = ["banking77", "blimp", "toxicity"]
SHORT = {"banking77": "Banking intents", "blimp": "Grammar", "toxicity": "Moderation"}
WHAT = {
    "banking77": "Route a bank customer's message to 1 of 77 intents",
    "blimp": "Pick the grammatical sentence of a pair (A or B)",
    "toxicity": "Flag an online comment as toxic or not",
}
# Hand-picked, non-offensive examples from the confirmation set (ids verified to exist below).
EXAMPLES = [
    ("blimp", "blimp-wh_vs_that_with_gap-178", "gpt-5.4-mini"),
    ("banking77", "banking77-test-02552", "gpt-5.4-mini"),
    ("toxicity", "toxicity-test-002273", "claude-haiku-4-5"),
]
REVIEW_COST = 0.25


def _jl(p: Path) -> list[dict]:
    with p.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def build_data() -> dict:
    cards = {t: json.loads((ROOT / f"reports/confirm/verdicts/{t}.json").read_text(encoding="utf-8")) for t in TASKS}
    conf = json.loads((ROOT / "reports/confirm/confirm_results.json").read_text(encoding="utf-8"))
    spend = json.loads((ROOT / "runs/spend.json").read_text(encoding="utf-8"))
    res = _jl(ROOT / "runs/results_confirm.jsonl")
    by = defaultdict(dict)
    for r in res:
        by[(r["item_id"], r["model"])][r["mode"]] = r

    tasks = {}
    for t in TASKS:
        c = cards[t]
        pol = [p for p in conf["tasks"][t]["policies"] if p.get("fitted")]
        passing = sorted([p for p in pol if p["passes"]], key=lambda p: (-p["coverage"], p["total_cost_per_1k"]))
        cheapest_total = min(passing, key=lambda p: p["total_cost_per_1k"]) if passing else None
        tasks[t] = {
            "id": t, "short": SHORT[t], "name": load(t).name, "what": WHAT[t],
            "n": conf["tasks"][t]["n_confirm"], "target_accuracy": c["target_accuracy"],
            "configs": [{
                "model": x["model"], "mode": x["mode"], "acc": x["accuracy"]["acc"], "ci": x["accuracy"]["ci"],
                "cost": x["cost_per_1k"], "lat": x["latency_median_s"], "think": x["mean_reasoning_tokens"],
                "ece": x["calibration"]["ece"], "overconf": x["calibration"]["overconfidence"],
                "rel": x["calibration"]["reliability"],
            } for x in c["configs"]],
            "per_model": {m: {"verdict": v["mode_verdict"]["verdict"], "diff": v["diff"]["diff"],
                              "ci": v["diff"]["ci"], "ratio": v["cost_ratio"],
                              "cpec": v["mode_verdict"].get("cost_per_extra_correct_usd"),
                              "r2w": v["flips"]["right_to_wrong"], "w2r": v["flips"]["wrong_to_right"],
                              "overthink": v["overthinking_risk"]}
                          for m, v in c["per_model"].items()},
            "best_policy": passing[0] if passing else None,
            "cheapest_total": cheapest_total,
            "policies": [{"name": p["policy"], "kind": p["kind"], "mode": p["mode"], "floor": p["fitted_c"],
                          "cov": p["coverage"], "prec": p["precision"], "lb": p["precision_lower"],
                          "pass": p["passes"], "api": p["api_cost_per_1k"], "total": p["total_cost_per_1k"],
                          "disc_prec": p["discovery_at_fit"]["precision"]} for p in pol],
        }

    examples = []
    for t, iid, m in EXAMPLES:
        item = next(it for it in load(t).items("confirm") if it["id"] == iid)
        g, r = by[(iid, m)]["gut"], by[(iid, m)]["reasoned"]
        examples.append({"task": t, "short": SHORT[t], "model": m, "input": item["input"], "gold": item["gold"],
                         "gut": [g["answer"], g["confidence"], g["correct"]],
                         "rea": [r["answer"], r["confidence"], r["correct"]]})

    # The starting idea to test: "answers given at >= 90% confidence are ~99% right". Checked on the confirmation set.
    from .threshold import wilson_lower
    acc90 = defaultdict(lambda: [0, 0, 0])
    for r in res:
        k = (r["task"], r["model"], r["mode"])
        acc90[k][2] += 1
        if r["status"] == "ok" and r["confidence"] >= 90:
            acc90[k][0] += 1
            acc90[k][1] += bool(r["correct"])
    rule90 = [{"task": t, "model": m, "mode": mo, "n": n, "correct": c, "prec": c / n if n else None,
               "lb": wilson_lower(c, n) if n else None, "cov": n / N}
              for (t, m, mo), (n, c, N) in sorted(acc90.items())]

    h = conf["hypotheses"]
    rep = conf["replications"]
    models = conf["models"]
    pm = lambda t, m: tasks[t]["per_model"][m]

    def status(k, n):
        return "held" if k == n else ("partly held" if k > 0 else "failed")

    h1k = sum(1 for m in models if rep["H1_overconf_tox_minus_blimp"][m]["ci"][0] > 0)
    h2k = sum(1 for m in models if rep["H2_mode_verdicts"]["banking77"][m] == "Use fast mode")
    h3g = sum(1 for m in models if rep["H3_gut_conf_usable"]["blimp"][m])
    h3b = sum(1 for m in models if rep["H3_gut_conf_usable"]["banking77"][m])
    nice = {"gpt-5.4-mini": "gpt-5.4-mini", "claude-haiku-4-5": "Haiku 4.5", "gemini-3.5-flash": "Gemini 3.5 Flash"}
    worst = min(models, key=lambda m: pm("toxicity", m)["diff"])
    h4 = conf["tasks"]
    scorecard = [
        {"claim": "Thinking won't improve moderation",
         "status": "held" if h["H7"]["result"] == "SUPPORTED" else "failed",
         "detail": f"Fast mode won for all 3 models. {nice[worst]} got {abs(pm('toxicity', worst)['diff']) * 100:.1f} pts "
                   f"worse with thinking."},
        {"claim": "Models are more overconfident on moderation than on grammar", "status": status(h1k, 3),
         "detail": f"True for {h1k} of 3 models (the gap's confidence interval stays above zero)."},
        {"claim": "Thinking isn't worth paying for on banking intents", "status": status(h2k, 3),
         "detail": f"{h2k} of 3 models: fast mode. gpt-5.4-mini still gains "
                   f"{pm('banking77', 'gpt-5.4-mini')['diff'] * 100:+.1f} pts from thinking."},
        {"claim": "A model's own fast-mode confidence is enough to auto-accept safely", "status": status(h3g + h3b, 6),
         "detail": f"Grammar: works for {h3g} of 3 models. Banking: {h3b} of 3."},
        {"claim": "Two cheap fast models agreeing beats one model's own confidence",
         "status": "failed" if h["H4"]["result"] == "NOT SUPPORTED" else "partly held",
         "detail": f"Banking: no agreement rule was safe. Grammar: the best fast-mode agreement rule covered "
                   f"{h4['blimp']['h4']['best_gut_agree_coverage'] * 100:.0f}%, but one model thinking covered "
                   f"{h4['blimp']['h4']['best_self_coverage'] * 100:.0f}%."},
        {"claim": "Models stay just as confident on comments humans disagree about",
         "status": "failed" if h["H5"]["result"] == "NOT SUPPORTED" else "held",
         "detail": "Two of the three models do get a little less confident. Their accuracy drops much more, though."},
        {"claim": "When all 3 models agree on moderation, they're still wrong over 15% of the time",
         "status": "failed" if h["H6"]["result"] == "NOT SUPPORTED" else "held",
         "detail": f"They agreed on {h['H6']['unanimous_share'] * 100:.0f}% of comments and were right "
                   f"{h['H6']['precision_when_unanimous'] * 100:.1f}% of the time, just past the line we drew."},
    ]
    for sc, hid in zip(scorecard, ["H7", "H1", "H2", "H3", "H4", "H5", "H6"]):
        sc["id"] = hid
        sc["when"] = "before round 1" if hid in ("H1", "H2", "H3") else "after round 1"
    scorecard.sort(key=lambda r: r["id"])
    n_fit = sum(len(tasks[t]["policies"]) for t in TASKS)
    n_fail = sum(1 for t in TASKS for p in tasks[t]["policies"] if not p["pass"])
    return {
        "rule90": rule90, "repo": "https://github.com/atharva-729/llm-gut-check",
        "n_pilot": len(load("banking77").items("pilot")),
        "scorecard": scorecard, "error_cost": 2.50, "spend": spend["by_split"],
        "n_disc": len(load("banking77").items("main")),
        "n_calls_main": len(_jl(ROOT / "runs/results_main.jsonl")),
        "tasks": tasks, "examples": examples, "review_cost": REVIEW_COST,
        "n_calls_confirm": len(res), "spend_total": spend["total_usd"],
        "spend_confirm": spend["by_split"].get("confirm", 0.0),
        "hyp": {k: v["result"] for k, v in h.items()},
        "h6": {"share": h["H6"]["unanimous_share"], "prec": h["H6"]["precision_when_unanimous"]},
        "shrink": {"fitted": n_fit, "failed": n_fail,
                   "b77_fitted": len(tasks["banking77"]["policies"]),
                   "b77_failed": sum(1 for p in tasks["banking77"]["policies"] if not p["pass"])},
    }


def build(out: Path | None = None) -> Path:
    out = out or ROOT / "docs" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(build_data(), separators=(",", ":"))
    html = (Path(__file__).parent / "site_template.html").read_text(encoding="utf-8")
    out.write_text(html.replace("/*__DATA__*/null", data), encoding="utf-8")
    return out

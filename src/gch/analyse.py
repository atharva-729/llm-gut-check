"""Phase 4: metrics per task x model x mode, thresholds, verdict cards (md + json) and plotly charts."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import metrics, threshold, verdict
from .tasks import load

ROOT = Path(__file__).resolve().parents[2]


def _group(results: list[dict]) -> dict:
    g = defaultdict(lambda: defaultdict(dict))
    for r in results:
        g[r["task"]][(r["model"], r["mode"])][r["item_id"]] = r
    return g


def analyse_task(task_id: str, cells: dict, target_precision: float, min_n: int) -> dict:
    task = load(task_id)
    configs, per_model = [], {}
    for (model, mode), items in sorted(cells.items()):
        rows = list(items.values())
        acc = metrics.accuracy(rows)
        configs.append({
            "model": model, "mode": mode, **metrics.cost_latency(rows),
            "accuracy": acc, "acc_ci_lo": acc["ci"][0],
            "calibration": metrics.calibration(rows),
            "parse_fail": sum(1 for r in rows if r["status"] == "parse_fail"),
            "threshold": threshold.search(rows, target_precision, min_n),
            "threshold_99": threshold.search(rows, 0.99, min_n),
        })
    for model in sorted({m for m, _ in cells}):
        gut, rea = cells.get((model, "gut"), {}), cells.get((model, "reasoned"), {})
        if not gut or not rea:
            continue
        cg = next(c for c in configs if c["model"] == model and c["mode"] == "gut")
        cr = next(c for c in configs if c["model"] == model and c["mode"] == "reasoned")
        diff = metrics.paired_diff(gut, rea)
        fl = metrics.flips(gut, rea)
        per_model[model] = {
            "diff": diff, "flips": fl,
            "mode_verdict": verdict.mode_choice(diff, cg["cost_per_1k"], cr["cost_per_1k"], diff["n"]),
            "overthinking_risk": verdict.overthinking(fl),
            "confidence_usable": {mode: verdict.confidence_usable(c["threshold"])
                                  for mode, c in (("gut", cg), ("reasoned", cr))},
            "cost_ratio": cr["cost_per_1k"] / cg["cost_per_1k"] if cg["cost_per_1k"] else None,
        }
    return {
        "task": task_id, "name": task.name, "target_accuracy": task.target_accuracy,
        "target_precision": target_precision, "configs": configs, "per_model": per_model,
        "cheapest": verdict.cheapest(configs, task.target_accuracy),
    }


# ---------------------------------------------------------------- rendering
def _pct(x, d=1):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:.{d}f}%"


def card_md(a: dict) -> str:
    L = [f"# Verdict card: {a['name']}", ""]
    ch = a["cheapest"]
    L.append("## Recommendation")
    if ch["by_accuracy"]:
        c = ch["by_accuracy"]
        L.append(f"- **Cheapest config meeting {_pct(a['target_accuracy'], 0)} accuracy (CI lower bound):** "
                 f"`{c['model']}` · **{c['mode']}** at ${c['cost_per_1k']:.2f} per 1,000 items.")
    else:
        L.append(f"- **No configuration's accuracy CI lower bound reaches {_pct(a['target_accuracy'], 0)}.**")
    if ch["by_auto_accept"]:
        c = ch["by_auto_accept"]
        L.append(f"- **Best auto-accept set at {_pct(a['target_precision'], 0)} precision:** `{c['model']}` · "
                 f"**{c['mode']}**, accept when confidence ≥ {c['threshold']:.0f}: covers **{_pct(c['coverage'], 0)}** "
                 f"of items; the rest go to human review (${c['cost_per_1k']:.2f} per 1k).")
    else:
        L.append(f"- **No configuration has a safe auto-accept threshold at {_pct(a['target_precision'], 0)} "
                 f"precision with ≥30% coverage.** Send everything to review, or don't use confidence.")
    L.append("")
    for model, pm in a["per_model"].items():
        v, d, f = pm["mode_verdict"], pm["diff"], pm["flips"]
        L.append(f"### `{model}`: {v['verdict']}")
        s = (f"Thinking changes accuracy by {d['diff'] * 100:+.1f} pts (95% CI {d['ci'][0] * 100:+.1f} to "
             f"{d['ci'][1] * 100:+.1f}) at {pm['cost_ratio']:.1f}× the cost ({v['why']}).")
        if v.get("cost_per_extra_correct_usd") is not None:
            s += f" Cost per extra correct answer: ${v['cost_per_extra_correct_usd']:.4f}."
        L.append(s)
        L.append(f"Flips: {f['wrong_to_right']} fixed, **{f['right_to_wrong']} overthought** (right → wrong, "
                 f"{_pct(f['overthinking_rate'])} of items), {f['wrong_to_wrong_changed']} wrong → different wrong."
                 + (" **⚠ Overthinking risk.**" if pm["overthinking_risk"] else ""))
        L.append("")
    L.append("## Fast vs reasoned, all configurations")
    L.append("| Model | Mode | Accuracy (95% CI) | $ / 1k items | Latency median / p90 | Thinking tok/item | "
             "ECE | Overconfidence | Auto-accept @95% (coverage) | @99% | Parse fails |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for c in a["configs"]:
        acc, cal, th, th99 = c["accuracy"], c["calibration"], c["threshold"], c["threshold_99"]
        tcell = f"≥{th['threshold']:.0f} ({_pct(th['coverage'], 0)})" if th["found"] else "none"
        t99 = f"≥{th99['threshold']:.0f} ({_pct(th99['coverage'], 0)})" if th99["found"] else "none"
        L.append(f"| {c['model']} | {c['mode']} | {_pct(acc['acc'])} ({_pct(acc['ci'][0])}–{_pct(acc['ci'][1])}) | "
                 f"${c['cost_per_1k']:.2f} | {c['latency_median_s']:.1f}s / {c['latency_p90_s']:.1f}s | "
                 f"{c['mean_reasoning_tokens']:.0f} | {cal['ece']:.3f} | {cal['overconfidence'] * 100:+.1f} pts | "
                 f"{tcell} | {t99} | {c['parse_fail']} |")
    L.append("")
    L.append(f"Notes: n = {a['configs'][0]['accuracy']['n']} items. Parse failures count as wrong. The 99% target needs "
             f"≥{threshold.min_all_correct_n(0.99)} all-correct items above the threshold, so with this sample it is "
             f"expected to show 'none'. Haiku thinking tokens are estimated (output − visible answer).")
    L.append("")
    L.append("Charts: `frontier_<task>.html` (cost vs accuracy), `reliability_<task>.html` (calibration).")
    return "\n".join(L)


def charts(a: dict, outdir: Path) -> None:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    colors = {"gpt-5.4-mini": "#2a6fdb", "claude-haiku-4-5": "#d9822b"}
    fig = go.Figure()
    for c in a["configs"]:
        acc = c["accuracy"]
        fig.add_trace(go.Scatter(
            x=[c["cost_per_1k"]], y=[acc["acc"] * 100], mode="markers+text",
            marker=dict(size=14, color=colors.get(c["model"], "#666"),
                        symbol="circle" if c["mode"] == "gut" else "diamond"),
            error_y=dict(type="data", symmetric=False, array=[(acc["ci"][1] - acc["acc"]) * 100],
                         arrayminus=[(acc["acc"] - acc["ci"][0]) * 100]),
            text=[f"{c['model']} · {c['mode']}"], textposition="top center", name=f"{c['model']} · {c['mode']}"))
    fig.add_hline(y=a["target_accuracy"] * 100, line_dash="dot", annotation_text="target accuracy")
    fig.update_layout(title=f"{a['name']}: cost vs accuracy (● gut, ◆ reasoned)", template="plotly_white",
                      xaxis_title="USD per 1,000 items (log)", yaxis_title="Accuracy % (95% CI)",
                      xaxis_type="log", showlegend=False)
    fig.write_html(outdir / f"frontier_{a['task']}.html", include_plotlyjs="cdn")

    models = sorted({c["model"] for c in a["configs"]})
    fig = make_subplots(rows=1, cols=len(models), subplot_titles=models)
    for i, m in enumerate(models, 1):
        fig.add_trace(go.Scatter(x=[0, 100], y=[0, 100], mode="lines", line=dict(color="#bbb", dash="dash"),
                                 showlegend=False), row=1, col=i)
        for c in a["configs"]:
            if c["model"] != m:
                continue
            rel = c["calibration"]["reliability"]
            fig.add_trace(go.Scatter(
                x=[b["mean_conf"] * 100 for b in rel], y=[b["acc"] * 100 for b in rel], mode="lines+markers",
                marker=dict(size=[max(6, min(30, b["n"] / 4)) for b in rel]),
                name=f"{m} · {c['mode']}", line=dict(dash="solid" if c["mode"] == "gut" else "dot"),
                hovertext=[f"n={b['n']}" for b in rel]), row=1, col=i)
    fig.update_layout(title=f"{a['name']}: reliability (stated confidence vs actual accuracy; marker size = items)",
                      template="plotly_white")
    fig.update_xaxes(title_text="Stated confidence %", range=[0, 102])
    fig.update_yaxes(title_text="Actual accuracy %", range=[0, 102])
    fig.write_html(outdir / f"reliability_{a['task']}.html", include_plotlyjs="cdn")


def run(results: list[dict], outdir: Path, target_precision: float, min_n: int) -> list[dict]:
    outdir.mkdir(parents=True, exist_ok=True)
    out = []
    for task_id, cells in sorted(_group(results).items()):
        a = analyse_task(task_id, cells, target_precision, min_n)
        (outdir / f"{task_id}.json").write_text(json.dumps(a, indent=2, default=str), encoding="utf-8")
        (outdir / f"{task_id}.md").write_text(card_md(a), encoding="utf-8")
        charts(a, outdir)
        out.append(a)
    return out

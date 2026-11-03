"""v1.1 confirmation report: H4-H7 + replications of H1-H3 + review economics. Output: reports/confirm/."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import agreement as ag
from . import queue
from .tasks import load

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "confirm"


def _verdict_cards() -> dict:
    d = OUT / "verdicts"
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in d.glob("*.json")}


def _overconf(items: dict, model: str) -> np.ndarray:
    return np.array([c[(model, "gut")]["confidence"] / 100 - (1.0 if c[(model, "gut")]["correct"] else 0.0)
                     for c in items.values() if ag._ok(c.get((model, "gut")))])


def build(models: list[str], tasks: list[str]) -> dict:
    disc = ag.index(queue.load_results("main"))
    conf = ag.index(queue.load_results("confirm"))
    cards = _verdict_cards()
    rep = {"models": models, "tasks": {}, "hypotheses": {}}
    for t in tasks:
        rows = ag.run_policies(disc[t], conf[t], models)
        rep["tasks"][t] = {"policies": rows, "n_confirm": len(conf[t]), "h4": ag.h4(rows)}

    # H4
    h4s = {t: rep["tasks"][t]["h4"]["holds"] for t in ("blimp", "banking77")}
    n = sum(h4s.values())
    rep["hypotheses"]["H4"] = {"per_task": h4s, "result": ["NOT SUPPORTED", "MIXED", "SUPPORTED"][n]}
    # H5
    meta = {it["id"]: it for it in load("toxicity").items("confirm")}
    h5 = ag.h5(conf["toxicity"], meta, models)
    h5["result"] = "SUPPORTED" if h5["supported"] else "NOT SUPPORTED"
    rep["hypotheses"]["H5"] = h5
    # H6
    h6 = ag.h6(conf["toxicity"], models, rep["tasks"]["toxicity"]["policies"])
    h6["result"] = "SUPPORTED" if h6["supported"] else "NOT SUPPORTED"
    rep["hypotheses"]["H6"] = h6
    # H7 (from the v1 verdict rule run on the confirmation set)
    tox = cards.get("toxicity", {}).get("per_model", {})
    h7 = {m: tox.get(m, {}).get("mode_verdict", {}).get("verdict") for m in models}
    rep["hypotheses"]["H7"] = {"per_model": h7,
                               "result": "SUPPORTED" if all(v == "Use fast mode" for v in h7.values())
                               else "NOT SUPPORTED"}
    # Replications
    rng = np.random.default_rng(20261104)
    h1 = {}
    for m in models:
        a, b = _overconf(conf["toxicity"], m), _overconf(conf["blimp"], m)
        boots = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(2000)]
        h1[m] = {"diff": float(a.mean() - b.mean()), "ci": [float(np.percentile(boots, 2.5)),
                                                            float(np.percentile(boots, 97.5))]}
    rep["replications"] = {
        "H1_overconf_tox_minus_blimp": h1,
        "H2_mode_verdicts": {t: {m: cards.get(t, {}).get("per_model", {}).get(m, {}).get("mode_verdict", {})
                                 .get("verdict") for m in models} for t in ("toxicity", "banking77")},
        "H3_gut_conf_usable": {t: {m: cards.get(t, {}).get("per_model", {}).get(m, {})
                                   .get("confidence_usable", {}).get("gut") for m in models}
                               for t in ("blimp", "banking77")},
    }
    return rep


def _f(x, pct=True, d=1):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return f"{x * 100:.{d}f}%" if pct else f"{x:.2f}"


def markdown(rep: dict) -> str:
    L = ["# v1.1 confirmation results", "",
         "Thresholds and agreement rules were **fitted on the 200-item discovery set** and **tested unchanged "
         "on 600 new items per task**, as pre-registered (PREREG.md, Addendum v1.1). Pass = Wilson 95% lower bound "
         "on precision ≥ 95% with ≥ 30 items accepted. Total cost assumes $0.25 per human review and $2.50 per wrong "
         "auto-accepted answer.", ""]
    L.append("## Hypotheses")
    for h, v in rep["hypotheses"].items():
        L.append(f"- **{h}: {v['result']}**")
    L.append("")
    for t, d in rep["tasks"].items():
        L.append(f"## {load(t).name} (n = {d['n_confirm']})")
        h = d["h4"]
        L.append(f"Best self-confidence policy: **{h['best_self'] or 'none passes'}** "
                 f"(coverage {_f(h['best_self_coverage'], d=0)}). Best gut-mode agreement policy: "
                 f"**{h['best_gut_agree'] or 'none passes'}** (coverage {_f(h['best_gut_agree_coverage'], d=0)}).")
        L.append("")
        L.append("| Policy | Floor (fit on discovery) | Coverage | Precision | Lower bound | Pass | API $/1k | "
                 "Total $/1k incl. review |")
        L.append("|---|---|---|---|---|---|---|---|")
        rows = sorted([r for r in d["policies"] if r.get("fitted")],
                      key=lambda r: (not r["passes"], -r["coverage"]))
        for r in rows:
            L.append(f"| {r['policy']} | ≥{r['fitted_c']} | {_f(r['coverage'], d=0)} | {_f(r['precision'])} | "
                     f"{_f(r['precision_lower'])} | {'✅' if r['passes'] else '❌'} | ${r['api_cost_per_1k']:.2f} | "
                     f"${r['total_cost_per_1k']:.0f} |")
        nf = [r["policy"] for r in d["policies"] if not r.get("fitted")]
        if nf:
            L.append(f"\nNot fitted on discovery (never reached 97% precision): {', '.join(nf)}.")
        L.append(f"\nBaseline, everything to human review: ${0.25 * 1000:.0f} per 1k items.\n")
    h5 = rep["hypotheses"]["H5"]["per_model"]
    L.append("## Toxicity: confidence vs human ambiguity (H5)")
    L.append("| Model | Accuracy, clear items | Accuracy, split items | Δ (95% CI) | Confidence, clear | "
             "Confidence, split | Δ (95% CI) |")
    L.append("|---|---|---|---|---|---|---|")
    for m, v in h5.items():
        L.append(f"| {m} | {_f(v['acc_clear'])} | {_f(v['acc_split'])} | {v['acc_diff'] * 100:+.1f} "
                 f"({v['acc_diff_ci'][0] * 100:+.1f}, {v['acc_diff_ci'][1] * 100:+.1f}) | {v['conf_clear']:.1f} | "
                 f"{v['conf_split']:.1f} | {v['conf_diff']:+.1f} ({v['conf_diff_ci'][0]:+.1f}, "
                 f"{v['conf_diff_ci'][1]:+.1f}) |")
    h6 = rep["hypotheses"]["H6"]
    L.append(f"\n**H6:** all three gut answers agree on {_f(h6['unanimous_share'], d=0)} of toxicity items, "
             f"but are right only {_f(h6['precision_when_unanimous'])} of the time when they do. "
             f"Any policy passes: {h6['any_policy_passes']}.")
    L.append(f"\n**H7 (toxicity mode verdicts):** {rep['hypotheses']['H7']['per_model']}")
    L.append("\n## Replications of v1 hypotheses on the confirmation set")
    for m, v in rep["replications"]["H1_overconf_tox_minus_blimp"].items():
        L.append(f"- H1 {m}: toxicity − BLiMP gut overconfidence {v['diff'] * 100:+.1f} pts "
                 f"(CI {v['ci'][0] * 100:+.1f} to {v['ci'][1] * 100:+.1f})")
    L.append(f"- H2 mode verdicts: {rep['replications']['H2_mode_verdicts']}")
    L.append(f"- H3 gut confidence usable: {rep['replications']['H3_gut_conf_usable']}")
    return "\n".join(L)


def charts(rep: dict) -> None:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    tasks = list(rep["tasks"])
    fig = make_subplots(rows=1, cols=len(tasks), subplot_titles=[load(t).name for t in tasks], shared_yaxes=True)
    sym = {"SELF": "circle", "AGREE": "diamond", "MAJ": "star"}
    for i, t in enumerate(tasks, 1):
        for r in rep["tasks"][t]["policies"]:
            if not r.get("fitted"):
                continue
            fig.add_trace(go.Scatter(
                x=[r["coverage"] * 100], y=[r["precision"] * 100], mode="markers",
                marker=dict(symbol=sym[r["kind"]], size=8 + min(25, r["api_cost_per_1k"] * 2),
                            color="#2a9d4b" if r["passes"] else "#c0392b",
                            line=dict(width=1, color="#333" if r["mode"] == "gut" else "#999")),
                error_y=dict(type="data", symmetric=False, array=[0],
                             arrayminus=[(r["precision"] - r["precision_lower"]) * 100]),
                hovertext=f"{r['policy']} floor≥{r['fitted_c']}<br>API ${r['api_cost_per_1k']:.2f}/1k",
                showlegend=False), row=1, col=i)
        fig.add_hline(y=95, line_dash="dot", row=1, col=i)
    fig.update_layout(title="Auto-accept policies on 600 new items: coverage vs precision "
                            "(● self-confidence, ◆ agreement, ★ majority; green = passes; size = API cost)",
                      template="plotly_white", height=500)
    fig.update_xaxes(title_text="Coverage: % of items auto-accepted", range=[0, 100])
    fig.update_yaxes(title_text="Precision % (bar = Wilson lower bound)", range=[60, 101], col=1)
    fig.write_html(OUT / "policies.html", include_plotlyjs="cdn")


def run(models: list[str], tasks: list[str]) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    rep = build(models, tasks)
    (OUT / "confirm_results.json").write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    (OUT / "confirm_results.md").write_text(markdown(rep), encoding="utf-8")
    charts(rep)
    return rep

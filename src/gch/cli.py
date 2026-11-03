"""gch — Gut-Check Harness CLI (lean v1)."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from . import budget, queue

ROOT = Path(__file__).resolve().parents[2]


def cfg() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


def _jobs(c: dict, split: str, task: str | None) -> list[dict]:
    fn = {"main": "items.jsonl", "pilot": "pilot.jsonl", "confirm": "confirm.jsonl"}[split]
    tasks = [task] if task else [t for t in c["tasks"] if (ROOT / "tasks" / t / fn).exists()]
    return queue.build_jobs(tasks, c["models"], c["modes"], split)


def cmd_probe(a):
    from . import probe
    rows = probe.run(cfg()["models"], ROOT / "runs" / "probe.json")
    budget.add_spend(sum(r["cost_usd"] for r in rows), "probe")


def cmd_plan(a):
    c = cfg()
    measured = budget.measured_per_call(queue.load_results("pilot"))
    for split in (["pilot", "main", "confirm"] if a.split == "all" else [a.split]):
        print(f"\n=== {split} ===")
        jobs = [j for j in _jobs(c, split, a.task) if queue.job_key(j) not in queue.done_keys(split)]
        budget.print_plan(budget.plan(jobs, measured, c["retry_overhead"]), c["budget_usd"])


def _run(split: str, a):
    c = cfg()
    jobs = _jobs(c, split, a.task)
    done = queue.done_keys(split)
    todo = [j for j in jobs if queue.job_key(j) not in done]
    measured = budget.measured_per_call(queue.load_results("pilot"))
    est = budget.plan(todo, measured, c["retry_overhead"])["total_usd"]
    remaining = c["budget_usd"] - budget.spent()
    print(f"{split}: {len(todo)} jobs to run ({len(jobs) - len(todo)} already done). "
          f"Estimate ${est:.2f}, budget remaining ${remaining:.2f}.")
    if est > remaining and not a.force:
        sys.exit("Refusing to start: estimate exceeds remaining budget. Use --force to override.")
    stats = queue.run(todo, split, c["concurrency"], c["seed"])
    print(json.dumps(stats))


def cmd_pilot(a):
    _run("pilot", a)


def cmd_run(a):
    _run(a.split, a)


def cmd_status(a):
    """Counts and cost only — never accuracy (no peeking before the queue is complete)."""
    c = cfg()
    for split in ("pilot", "main", "confirm"):
        jobs = _jobs(c, split, None)
        res = queue.load_results(split)
        if not res and split != "pilot":
            print(f"\n{split}: 0/{len(jobs)} done")
            continue
        by = defaultdict(Counter)
        cost = defaultdict(float)
        for r in res:
            k = (r["task"], r["model"], r["mode"])
            by[k][r["status"]] += 1
            cost[k] += r.get("cost_usd", 0.0)
        print(f"\n{split}: {len(res)}/{len(jobs)} done")
        print(f"{'task':<11}{'model':<18}{'mode':<10}{'ok':>5}{'parse_fail':>11}{'$':>9}")
        for k in sorted(by):
            print(f"{k[0]:<11}{k[1]:<18}{k[2]:<10}{by[k]['ok']:>5}{by[k]['parse_fail']:>11}{cost[k]:>9.3f}")
    print(f"\nTotal spend logged: ${budget.spent():.3f} of ${c['budget_usd']:.2f}")


def cmd_analyse(a):
    from . import analyse
    c = cfg()
    split = a.split
    res = queue.load_results(split)
    expected = len(_jobs(c, split, None))
    if split != "pilot" and len(res) < expected and not a.force:
        sys.exit(f"Queue incomplete ({len(res)}/{expected}). Finish `gch run` first (or --force).")
    outdir = ROOT / {"main": "reports/verdicts", "confirm": "reports/confirm/verdicts",
                     "pilot": "runs/pilot_reports"}[split]
    cards = analyse.run(res, outdir, c["target_precision"], c["min_items_above_threshold"])
    print(f"Wrote {len(cards)} verdict cards to {outdir}")


def cmd_confirm_report(a):
    from . import confirm_report
    c = cfg()
    res = queue.load_results("confirm")
    expected = len(_jobs(c, "confirm", None))
    if len(res) < expected and not a.force:
        sys.exit(f"Confirmation queue incomplete ({len(res)}/{expected}).")
    rep = confirm_report.run(c["models"], c["tasks"])
    for h, v in rep["hypotheses"].items():
        print(h, v["result"])


def cmd_site(a):
    from . import site
    print(f"Wrote {site.build()}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="gch")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("probe").set_defaults(f=cmd_probe)
    sp = sub.add_parser("plan")
    sp.add_argument("--split", default="all", choices=["all", "pilot", "main", "confirm"])
    sp.add_argument("--task")
    sp.set_defaults(f=cmd_plan)
    for name, fn in (("pilot", cmd_pilot), ("run", cmd_run)):
        sp = sub.add_parser(name)
        sp.add_argument("--task")
        if name == "run":
            sp.add_argument("--split", default="main", choices=["main", "confirm"])
        sp.add_argument("--force", action="store_true")
        sp.set_defaults(f=fn)
    sub.add_parser("status").set_defaults(f=cmd_status)
    sp = sub.add_parser("analyse")
    sp.add_argument("--split", default="main", choices=["pilot", "main", "confirm"])
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(f=cmd_analyse)
    sub.add_parser("site").set_defaults(f=cmd_site)
    sp = sub.add_parser("confirm-report")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(f=cmd_confirm_report)
    a = p.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    main()

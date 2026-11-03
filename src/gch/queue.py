"""Resumable job queue. One result line per (split, task, item, model, mode) in runs/results_<split>.jsonl."""
from __future__ import annotations

import json
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import budget, llm
from .models import MODELS
from .parse import parse_answer
from .tasks import load

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs"


def results_path(split: str) -> Path:
    return RUNS / f"results_{split}.jsonl"


def job_key(j: dict) -> str:
    return f"{j['task']}|{j['item_id']}|{j['model']}|{j['mode']}"


def build_jobs(tasks: list[str], models: list[str], modes: list[str], split: str) -> list[dict]:
    jobs = []
    for t in tasks:
        for it in load(t).items(split):
            for m in models:
                for mode in modes:
                    jobs.append({"task": t, "item_id": it["id"], "model": m, "mode": mode, "split": split})
    return jobs


def done_keys(split: str) -> set[str]:
    p = results_path(split)
    if not p.exists():
        return set()
    with p.open(encoding="utf-8") as f:
        return {job_key(json.loads(l)) for l in f if l.strip()}


def load_results(split: str) -> list[dict]:
    p = results_path(split)
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def run_job(job: dict, items_by_id: dict) -> dict:
    task = load(job["task"])
    model = MODELS[job["model"]]
    item = items_by_id[(job["task"], job["item_id"])]
    total_cost, attempts, rec, parsed = 0.0, 0, None, None
    for attempt in range(2):  # one retry on parse failure
        attempts = attempt + 1
        rec = llm.call(model, job["mode"], task.system_prompt, item["input"], task.schema, attempt=attempt)
        total_cost += rec.get("cost_usd", 0.0) if not rec.get("from_cache") else 0.0
        if rec.get("error"):
            break
        parsed = parse_answer(rec.get("text", ""), task.options)
        if parsed.ok:
            break
    status = "error" if rec.get("error") else ("ok" if parsed and parsed.ok else "parse_fail")
    return {
        **job,
        "gold": item["gold"],
        "status": status,
        "answer": parsed.answer if parsed else None,
        "confidence": parsed.confidence if parsed else None,
        "correct": (parsed.answer == item["gold"]) if parsed and parsed.ok else None,
        "parse_reason": parsed.reason if parsed else None,
        "attempts": attempts,
        "usage": rec.get("usage", {}),
        "cost_usd": rec.get("cost_usd", 0.0),
        "new_spend_usd": total_cost,
        "latency_s": rec.get("latency_s"),
        "finish": rec.get("finish"),
        "error": rec.get("error"),
        "raw_text": (rec.get("text") or "")[:2000],
    }


def run(jobs: list[dict], split: str, concurrency: dict[str, int], seed: int, progress_every: int = 50) -> dict:
    done = done_keys(split)
    todo = [j for j in jobs if job_key(j) not in done]
    random.Random(seed).shuffle(todo)  # random order so a partial run is unbiased
    items_by_id = {(t, it["id"]): it for t in {j["task"] for j in todo} for it in load(t).items(split)}
    sems = {p: threading.BoundedSemaphore(n) for p, n in concurrency.items()}
    lock = threading.Lock()
    out = results_path(split)
    out.parent.mkdir(parents=True, exist_ok=True)
    stats = {"todo": len(todo), "done": 0, "spend": 0.0, "errors": 0, "parse_fail": 0}

    def work(j):
        with sems[MODELS[j["model"]].provider]:
            return run_job(j, items_by_id)

    with ThreadPoolExecutor(max_workers=sum(concurrency.values())) as ex, out.open("a", encoding="utf-8") as f:
        futs = [ex.submit(work, j) for j in todo]
        for fut in as_completed(futs):
            r = fut.result()
            with lock:
                if r["status"] == "error":
                    stats["errors"] += 1
                    # errors are not written, so a re-run retries them
                else:
                    f.write(json.dumps(r) + "\n")
                    f.flush()
                if r["status"] == "parse_fail":
                    stats["parse_fail"] += 1
                stats["done"] += 1
                stats["spend"] += r["new_spend_usd"]
                budget.add_spend(r["new_spend_usd"], split)
                if stats["done"] % progress_every == 0 or stats["done"] == len(todo):
                    print(f"  {stats['done']}/{len(todo)} jobs  spend ${stats['spend']:.3f}  "
                          f"errors {stats['errors']}  parse_fail {stats['parse_fail']}", flush=True)
    return stats

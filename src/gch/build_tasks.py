"""Build the demo task packs (lean version: banking77, blimp, toxicity).

Run with:  PYTHONPATH=src python -m gch.build_tasks            (items.jsonl + pilot.jsonl)
           PYTHONPATH=src python -m gch.build_tasks --confirm  (confirm.jsonl only)

Raw downloads are cached under tasks/_raw/ so reruns are offline and
idempotent. All sampling uses a fixed seed (SEED) with one independent
random.Random per task, so outputs are byte-identical across runs.
"""

from __future__ import annotations

import csv
import io
import json
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

import requests

SEED = 20261103
CONFIRM_SEED = 20261104
FETCH_DATE = "2026-11-03"
ROOT = Path(__file__).resolve().parents[2]
TASKS = ROOT / "tasks"
RAW = TASKS / "_raw"

HF_ROWS = "https://datasets-server.huggingface.co/rows"
HF_SPLITS = "https://datasets-server.huggingface.co/splits"

N_MAIN = 200
N_PILOT = 10
N_CONFIRM = 600
CONFIRM_HEADING = "## Confirmation set"


# --------------------------------------------------------------------------- utils


def norm_text(s: str) -> str:
    return " ".join(s.casefold().split())


def _get(url: str, params: dict | None = None, tries: int = 10) -> requests.Response:
    """GET with polite pacing and exponential backoff (datasets-server rate-limits with 429)."""
    last: Exception | None = None
    for i in range(tries):
        time.sleep(0.5)
        wait = min(120.0, 5.0 * 2**i)
        try:
            r = requests.get(url, params=params, timeout=60)
            if r.status_code == 200:
                return r
            last = RuntimeError(f"HTTP {r.status_code} for {r.url}: {r.text[:120]}")
            ra = r.headers.get("Retry-After")
            if ra and ra.isdigit():
                wait = max(wait, float(ra))
        except requests.RequestException as e:  # pragma: no cover - network
            last = e
        print(f"[build_tasks] retry {i + 1}/{tries} in {wait:.0f}s: {last}", flush=True)
        time.sleep(wait)
    raise RuntimeError(f"download failed: {url} {params}") from last


def cached_text(path: Path, url: str, params: dict | None = None) -> str:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        text = _get(url, params).text
        path.write_text(text, encoding="utf-8")
    return path.read_text(encoding="utf-8")


def hf_rows(dataset: str, config: str, split: str, offset: int, length: int, cache: Path) -> list[dict]:
    """Fetch rows [offset, offset+length) via datasets-server, 100 per page, cached per page."""
    out: list[dict] = []
    for start in range(offset, offset + length, 100):
        n = min(100, offset + length - start)
        page = cache / f"{split}_{start:08d}_{n}.json"
        txt = cached_text(
            page, HF_ROWS,
            {"dataset": dataset, "config": config, "split": split, "offset": start, "length": n},
        )
        out.extend(json.loads(txt)["rows"])
    return out


def write_jsonl(path: Path, items: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def write_source(path: Path, text: str) -> None:
    """Write SOURCE.md, preserving an existing confirmation-set section (written by --confirm)."""
    tail = ""
    if path.exists():
        old = path.read_text(encoding="utf-8")
        i = old.find("\n" + CONFIRM_HEADING)
        if i >= 0:
            tail = old[i:]
    write_text(path, text.rstrip("\n") + "\n" + tail if tail else text)


def set_confirm_section(path: Path, section: str) -> None:
    """Replace (or append) the confirmation-set section at the end of SOURCE.md."""
    old = path.read_text(encoding="utf-8")
    i = old.find("\n" + CONFIRM_HEADING)
    head = old[:i] if i >= 0 else old
    write_text(path, head.rstrip("\n") + "\n\n" + section.strip("\n") + "\n")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def used_items(task: str) -> list[dict]:
    """Already-released main + pilot items (read from disk, never regenerated here)."""
    d = TASKS / task
    return read_jsonl(d / "items.jsonl") + read_jsonl(d / "pilot.jsonl")


def task_yaml(*, name, task_id, answer_type, instructions, target_accuracy, licence, source_url,
              options=None, options_file=None) -> str:
    lines = [
        f"name: {json.dumps(name)}",
        f"task_id: {task_id}",
        f"answer_type: {answer_type}",
    ]
    if options is not None:
        lines.append("options: [" + ", ".join(json.dumps(o) for o in options) + "]")
    else:
        lines.append(f"options_file: {options_file}")
    lines += [
        f"instructions: {json.dumps(instructions)}",
        "target_precision: 0.95",
        f"target_accuracy: {target_accuracy}",
        f"licence: {json.dumps(licence)}",
        f"source_url: {json.dumps(source_url)}",
    ]
    return "\n".join(lines) + "\n"


def dist_table(counter: Counter) -> str:
    return "\n".join(f"| {k} | {v} |" for k, v in sorted(counter.items()))


# --------------------------------------------------------------------------- banking77

B77_BASE = "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data"


def _b77_splits() -> dict[str, list[dict]]:
    raw = RAW / "banking77"
    splits = {}
    for split in ("train", "test"):
        txt = cached_text(raw / f"{split}.csv", f"{B77_BASE}/{split}.csv")
        splits[split] = [
            {"row": i, "text": r["text"], "category": r["category"]}
            for i, r in enumerate(csv.DictReader(io.StringIO(txt)))
        ]
    return splits


def _b77_item(r: dict, split: str) -> dict:
    return {
        "id": f"banking77-{split}-{r['row']:05d}",
        "input": r["text"],
        "gold": r["category"],
        "meta": {"split": split, "row": r["row"]},
    }


def build_banking77() -> dict:
    rng = random.Random(SEED)
    splits = _b77_splits()
    labels = sorted({r["category"] for r in splits["train"]} | {r["category"] for r in splits["test"]})
    assert len(labels) == 77, len(labels)

    # Main: stratified from test. Every intent gets 2; 46 random distinct intents get a 3rd.
    test = splits["test"]
    seen_norm: set[str] = set()
    by_label: dict[str, list[dict]] = defaultdict(list)
    for r in test:  # drop duplicate texts within test (keep first occurrence)
        k = norm_text(r["text"])
        if k in seen_norm:
            continue
        seen_norm.add(k)
        by_label[r["category"]].append(r)
    extra = N_MAIN - 2 * len(labels)
    extra_labels = set(rng.sample(labels, extra))
    main_rows = []
    for lab in labels:
        k = 3 if lab in extra_labels else 2
        main_rows.extend(rng.sample(by_label[lab], k))
    rng.shuffle(main_rows)

    # Pilot: 10 from train, distinct intents, text not present anywhere in test.
    test_norm = {norm_text(r["text"]) for r in test}
    pilot_labels = rng.sample(labels, N_PILOT)
    train_by_label: dict[str, list[dict]] = defaultdict(list)
    for r in splits["train"]:
        if norm_text(r["text"]) not in test_norm:
            train_by_label[r["category"]].append(r)
    pilot_rows = [rng.choice(train_by_label[lab]) for lab in pilot_labels]

    main = [_b77_item(r, "test") for r in main_rows]
    pilot = [_b77_item(r, "train") for r in pilot_rows]

    out = TASKS / "banking77"
    out.mkdir(parents=True, exist_ok=True)
    write_text(out / "options.txt", "\n".join(labels) + "\n")
    write_jsonl(out / "items.jsonl", main)
    write_jsonl(out / "pilot.jsonl", pilot)
    write_text(out / "task.yaml", task_yaml(
        name="Banking77 intent classification",
        task_id="banking77",
        answer_type="single_choice",
        options_file="options.txt",
        instructions="Classify the bank customer's message into exactly one of the listed intents. "
                     "Answer with the intent label exactly as written.",
        target_accuracy=0.90,
        licence="CC BY 4.0",
        source_url="https://github.com/PolyAI-LDN/task-specific-datasets/tree/master/banking_data",
    ))
    mc = Counter(it["gold"] for it in main)
    per_label = Counter(mc.values())
    write_source(out / "SOURCE.md", f"""# Banking77 task pack

- **Source:** PolyAI Banking77 — {B77_BASE}/test.csv and {B77_BASE}/train.csv
  (repo: https://github.com/PolyAI-LDN/task-specific-datasets; paper: Casanueva et al. 2020, arXiv:2003.04807)
- **Licence:** CC BY 4.0
- **Date fetched:** {FETCH_DATE}
- **Seed:** {SEED} (`random.Random(SEED)`, see `src/gch/build_tasks.py::build_banking77`)
- **Options:** `options.txt` = the 77 intent labels exactly as in the dataset's `category` column, sorted alphabetically.

## Main (`items.jsonl`) — test split
- Filter: exact duplicate texts within test (case/whitespace-normalised) dropped, keeping the first occurrence.
- Sampling: stratified by intent. Every one of the 77 intents gets 2 items; the remaining
  {extra} items go to {extra} distinct intents chosen at random (3 items each). Rows sampled uniformly within intent; order shuffled.
- Count: {len(main)}. Distribution: {per_label.get(2, 0)} intents × 2, {per_label.get(3, 0)} intents × 3.

## Pilot (`pilot.jsonl`) — train split
- 10 distinct intents chosen at random, one train row each, excluding any train text that also
  appears (normalised) anywhere in the test split.
- Count: {len(pilot)}. Intents: {", ".join(sorted(it["gold"] for it in pilot))}.

## Item format
`id` = `banking77-<split>-<row index in CSV, 0-based excluding header>`, `input` = query text, `gold` = intent label,
`meta` = {{split, row}}.
""")
    return {"main": len(main), "pilot": len(pilot), "main_dist": dict(per_label)}


# --------------------------------------------------------------------------- blimp

BLIMP_DS = "nyu-mll/blimp"
BLIMP_HUMAN_URL = ("https://raw.githubusercontent.com/alexwarstadt/blimp/master/"
                   "raw_results/summary/human_validation_summary.csv")
BLIMP_ROWS_PER_PARADIGM = 100  # first 100 pairs of each paradigm (of 1000)


def _blimp_meta() -> tuple[list[str], dict[str, float], dict[str, int]]:
    raw = RAW / "blimp"
    splits = json.loads(cached_text(raw / "splits.json", HF_SPLITS, {"dataset": BLIMP_DS}))
    paradigms = sorted(s["config"] for s in splits["splits"])
    assert len(paradigms) == 67, len(paradigms)

    human: dict[str, float] = {}
    human_count: dict[str, int] = {}
    htxt = cached_text(raw / "human_validation_summary.csv", BLIMP_HUMAN_URL)
    for r in csv.DictReader(io.StringIO(htxt)):
        if r.get("Condition") in paradigms:
            human[r["Condition"]] = round(float(r["total_mean"]), 4)
            human_count[r["Condition"]] = int(r["count"])
    return paradigms, human, human_count


def _blimp_item(p: str, r: dict, g: str, human: dict[str, float]) -> dict:
    a, b = (r["sentence_good"], r["sentence_bad"]) if g == "A" else (r["sentence_bad"], r["sentence_good"])
    meta = {
        "paradigm": p,
        "pair_id": r["pair_id"],
        "field": r.get("field"),
        "linguistics_term": r.get("linguistics_term"),
    }
    it = {"id": f"blimp-{p}-{r['pair_id']}", "input": f"A: {a}\nB: {b}", "gold": g}
    if p in human:
        it["human_ref"] = human[p]
        meta["human_agreement"] = human[p]
    it["meta"] = meta
    return it


def build_blimp() -> dict:
    rng = random.Random(SEED)
    raw = RAW / "blimp"
    paradigms, human, human_count = _blimp_meta()
    missing_human = [p for p in paradigms if p not in human]

    rows: dict[str, list[dict]] = {}
    for p in paradigms:
        rows[p] = [x["row"] for x in hf_rows(BLIMP_DS, p, "train", 0, BLIMP_ROWS_PER_PARADIGM, raw / p)]

    # Main: 3 per paradigm, except one random paradigm gets 2 (67*3 = 201 -> 200).
    short = rng.choice(paradigms)
    main_rows, used_sents = [], set()
    for p in paradigms:
        k = 2 if p == short else 3
        picks = rng.sample(rows[p], k)
        main_rows.extend((p, r) for r in picks)
        for r in picks:
            used_sents.update({norm_text(r["sentence_good"]), norm_text(r["sentence_bad"])})
    rng.shuffle(main_rows)

    # Pilot: 10 distinct random paradigms, one other row each, no sentence shared with main.
    main_keys = {(p, r["pair_id"]) for p, r in main_rows}
    pilot_rows = []
    for p in rng.sample(paradigms, N_PILOT):
        cands = [r for r in rows[p]
                 if (p, r["pair_id"]) not in main_keys
                 and norm_text(r["sentence_good"]) not in used_sents
                 and norm_text(r["sentence_bad"]) not in used_sents]
        pilot_rows.append((p, rng.choice(cands)))

    def make(rows_, n_a):
        # exactly n_a items with gold "A", rest "B", positions shuffled
        golds = ["A"] * n_a + ["B"] * (len(rows_) - n_a)
        rng.shuffle(golds)
        return [_blimp_item(p, r, g, human) for (p, r), g in zip(rows_, golds)]

    main = make(main_rows, N_MAIN // 2)
    pilot = make(pilot_rows, N_PILOT // 2)

    out = TASKS / "blimp"
    out.mkdir(parents=True, exist_ok=True)
    write_jsonl(out / "items.jsonl", main)
    write_jsonl(out / "pilot.jsonl", pilot)
    write_text(out / "task.yaml", task_yaml(
        name="BLiMP grammaticality (A/B)",
        task_id="blimp",
        answer_type="single_choice",
        options=["A", "B"],
        instructions="Which sentence is grammatically acceptable? Answer A or B.",
        target_accuracy=0.95,
        licence="CC BY 4.0",
        source_url="https://huggingface.co/datasets/nyu-mll/blimp",
    ))
    ga = Counter(it["gold"] for it in main)
    gp = Counter(it["gold"] for it in pilot)
    fields = Counter(it["meta"]["field"] for it in main)
    hvals = sorted(human.values())
    write_source(out / "SOURCE.md", f"""# BLiMP task pack

- **Source:** BLiMP (Warstadt et al. 2020, TACL, arXiv:1912.00582), Hugging Face `nyu-mll/blimp`
  via the datasets-server API ({HF_ROWS}), one config per paradigm, split `train` (the only split).
  Original repo: https://github.com/alexwarstadt/blimp
- **Licence:** CC BY 4.0 (stated in the BLiMP repo README and the HF dataset card)
- **Date fetched:** {FETCH_DATE}
- **Seed:** {SEED} (`random.Random(SEED)`, see `src/gch/build_tasks.py::build_blimp`)

## Candidate pool
- 67 paradigms; for each, the first {BLIMP_ROWS_PER_PARADIGM} minimal pairs (rows 0–{BLIMP_ROWS_PER_PARADIGM - 1}
  of 1000) were downloaded. No other filters.

## Main (`items.jsonl`)
- Stratified across paradigms: 3 random pairs per paradigm, except one randomly chosen paradigm
  (`{short}`) which gets 2 → {len(main)} items. Order shuffled.
- A/B order: exactly half of items have the grammatical sentence as A (assignment shuffled with the seed).
  Gold balance: A = {ga["A"]}, B = {ga["B"]}.
- Field distribution: {", ".join(f"{k} {v}" for k, v in sorted(fields.items()))}.

## Pilot (`pilot.jsonl`)
- 10 distinct paradigms chosen at random, one pair each, drawn from rows **not** used in main and sharing
  **no sentence** (normalised) with any main item. Gold balance: A = {gp["A"]}, B = {gp["B"]}.
- Count: {len(pilot)}.

## Human agreement
- Attached: **{"yes" if not missing_human else "partially"}** ({len(human)}/67 paradigms).
- Source: official BLiMP repo file `raw_results/summary/human_validation_summary.csv`
  ({BLIMP_HUMAN_URL}). Column `total_mean` = mean human accuracy on that paradigm's validation pairs
  (forced-choice, 5 annotators per pair; `count` = pairs validated, 98–100). This is the human
  validation reported in Warstadt et al. (2020).
- Stored as top-level `human_ref` and `meta.human_agreement` (same value, per paradigm, not per item).
  Range across paradigms: {hvals[0] if hvals else "n/a"} – {hvals[-1] if hvals else "n/a"}.
{"- Missing paradigms: " + ", ".join(missing_human) if missing_human else ""}
- Note: humans validated a subset of pairs per paradigm; it is not known whether those are the exact
  pairs sampled here, so treat `human_ref` as a paradigm-level difficulty indicator.

## Item format
`id` = `blimp-<paradigm>-<pair_id>`, `input` = `"A: <sentence>\\nB: <sentence>"`, `gold` = `A`|`B`,
`meta` = {{paradigm, pair_id, field, linguistics_term, human_agreement}}.
""")
    return {"main": len(main), "pilot": len(pilot), "main_AB": dict(ga), "pilot_AB": dict(gp),
            "human_attached": len(human)}


# --------------------------------------------------------------------------- toxicity

CC_DS = "google/civil_comments"
CC_MIN_LEN, CC_MAX_LEN = 20, 600
CC_TEST_SLICE = 6000  # rows 0..5999 of test
CC_VAL_SLICE = 1500  # rows 0..1499 of validation


def _cc_load(split: str, offset: int, n: int) -> list[dict]:
    """Rows [offset, offset+n) of a Civil Comments split: 20-600 chars, normalised duplicates dropped."""
    out, seen = [], set()
    for x in hf_rows(CC_DS, "default", split, offset, n, RAW / "civil_comments"):
        t = x["row"]["text"]
        k = norm_text(t)
        if not (CC_MIN_LEN <= len(t) <= CC_MAX_LEN) or k in seen:
            continue
        seen.add(k)
        out.append({"row": x["row_idx"], "text": t, "toxicity": float(x["row"]["toxicity"])})
    return out


def _cc_item(r: dict, split: str) -> dict:
    return {
        "id": f"toxicity-{split}-{r['row']:06d}",
        "input": r["text"],
        "gold": "YES" if r["toxicity"] >= 0.5 else "NO",
        "meta": {"split": split, "row_idx": r["row"], "toxicity": round(r["toxicity"], 6)},
    }


def build_toxicity() -> dict:
    rng = random.Random(SEED)
    test = _cc_load("test", 0, CC_TEST_SLICE)
    val = _cc_load("validation", 0, CC_VAL_SLICE)

    def pick(pool, n_yes, n_no, exclude: set[str]):
        pool = [r for r in pool if norm_text(r["text"]) not in exclude]
        yes = [r for r in pool if r["toxicity"] >= 0.5]
        no = [r for r in pool if r["toxicity"] < 0.5]
        assert len(yes) >= n_yes and len(no) >= n_no, (len(yes), len(no))
        sel = rng.sample(yes, n_yes) + rng.sample(no, n_no)
        rng.shuffle(sel)
        return sel, len(yes), len(no)

    main_rows, ty, tn = pick(test, 60, 140, set())
    pilot_rows, vy, vn = pick(val, 3, 7, {norm_text(r["text"]) for r in main_rows})

    main = [_cc_item(r, "test") for r in main_rows]
    pilot = [_cc_item(r, "validation") for r in pilot_rows]

    out = TASKS / "toxicity"
    out.mkdir(parents=True, exist_ok=True)
    write_jsonl(out / "items.jsonl", main)
    write_jsonl(out / "pilot.jsonl", pilot)
    write_text(out / "task.yaml", task_yaml(
        name="Toxicity (Civil Comments)",
        task_id="toxicity",
        answer_type="binary",
        options=["YES", "NO"],
        instructions="Is this online comment toxic (rude, disrespectful or unreasonable)? "
                     "Answer YES if toxic, NO if not.",
        target_accuracy=0.90,
        licence="CC0 1.0",
        source_url="https://huggingface.co/datasets/google/civil_comments",
    ))
    gm = Counter(it["gold"] for it in main)
    gp = Counter(it["gold"] for it in pilot)
    write_source(out / "SOURCE.md", f"""# Toxicity task pack (Civil Comments)

- **Source:** Civil Comments (Borkan et al. 2019, arXiv:1903.04561), Hugging Face `google/civil_comments`,
  config `default`, via the datasets-server API ({HF_ROWS}).
- **Licence:** CC0 1.0 (HF dataset card `license: cc0-1.0`; the original Civil Comments / Jigsaw
  Unintended Bias release is also CC0).
- **Date fetched:** {FETCH_DATE}
- **Seed:** {SEED} (`random.Random(SEED)`, see `src/gch/build_tasks.py::build_toxicity`)
- **Gold:** `toxicity` (fraction of annotators rating the comment toxic or very toxic) **≥ 0.5 → YES**, else NO.
  Raw score kept in `meta.toxicity`.

## Candidate pool (bounded slice, not the full 2M rows)
- Main: test split rows 0–{CC_TEST_SLICE - 1} (of 97,320). Pilot: validation split rows 0–{CC_VAL_SLICE - 1} (of 97,320).
- Filters: comment length **{CC_MIN_LEN}–{CC_MAX_LEN} characters** inclusive (Python `len` on the raw text);
  exact duplicate texts (case/whitespace-normalised) dropped within each split.
- After filtering: test pool {ty} YES / {tn} NO; validation pool {vy} YES / {vn} NO.

## Main (`items.jsonl`) — test split
- Stratified random sample: exactly 60 YES + 140 NO (30% toxic, fixed by design — the natural rate in the
  pool is {ty / (ty + tn):.1%}). Order shuffled. Count: {len(main)} (YES {gm["YES"]}, NO {gm["NO"]}).

## Pilot (`pilot.jsonl`) — validation split
- Exactly 3 YES + 7 NO, excluding any text identical (normalised) to a main item.
  Count: {len(pilot)} (YES {gp["YES"]}, NO {gp["NO"]}).

## Item format
`id` = `toxicity-<split>-<HF row_idx>`, `input` = comment text, `gold` = `YES`|`NO`,
`meta` = {{split, row_idx, toxicity}}.
""")
    return {"main": len(main), "pilot": len(pilot), "main_dist": dict(gm), "pilot_dist": dict(gp),
            "pool_test": (ty, tn), "pool_val": (vy, vn)}


# --------------------------------------------------------------------------- confirmation sets
#
# `confirm.jsonl` (N_CONFIRM fresh items per task) confirms findings made on the 200 main items.
# items.jsonl / pilot.jsonl are read from disk (never rebuilt here) and excluded by id and by
# normalised text (BLiMP: also by individual sentence). Sampling uses CONFIRM_SEED.


def _check_disjoint(task: str, confirm: list[dict], used: list[dict]) -> None:
    ids = [i["id"] for i in confirm]
    txt = [norm_text(i["input"]) for i in confirm]
    assert len(confirm) == N_CONFIRM, len(confirm)
    assert len(set(ids)) == N_CONFIRM and len(set(txt)) == N_CONFIRM, task
    assert not set(ids) & {i["id"] for i in used}, task
    assert not set(txt) & {norm_text(i["input"]) for i in used}, task


def confirm_banking77() -> dict:
    rng = random.Random(CONFIRM_SEED)
    used = used_items("banking77")
    used_norm = {norm_text(i["input"]) for i in used}
    test = _b77_splits()["test"]
    labels = [l for l in (TASKS / "banking77" / "options.txt").read_text(encoding="utf-8").splitlines() if l]
    assert len(labels) == 77

    seen: set[str] = set()
    by_label: dict[str, list[dict]] = defaultdict(list)
    for r in test:  # same filter as main: drop normalised duplicate texts (keep first)
        k = norm_text(r["text"])
        if k in seen:
            continue
        seen.add(k)
        if k not in used_norm:
            by_label[r["category"]].append(r)
    base = N_CONFIRM // len(labels)  # 7
    extra = N_CONFIRM - base * len(labels)  # 61
    extra_labels = set(rng.sample(labels, extra))
    rows = []
    for lab in labels:
        rows.extend(rng.sample(by_label[lab], base + (lab in extra_labels)))
    rng.shuffle(rows)
    confirm = [_b77_item(r, "test") for r in rows]
    _check_disjoint("banking77", confirm, used)

    out = TASKS / "banking77"
    write_jsonl(out / "confirm.jsonl", confirm)
    per_label = Counter(Counter(i["gold"] for i in confirm).values())
    pool = sum(len(v) for v in by_label.values())
    set_confirm_section(out / "SOURCE.md", f"""{CONFIRM_HEADING} (`confirm.jsonl`) — test split
- Purpose: {N_CONFIRM} fresh items to confirm findings made on the 200 main items. Built with
  `PYTHONPATH=src python -m gch.build_tasks --confirm` (does not touch `items.jsonl` / `pilot.jsonl`).
- **Seed:** {CONFIRM_SEED} (`random.Random(CONFIRM_SEED)`, see `src/gch/build_tasks.py::confirm_banking77`)
- Source rows: test split (`test.csv`, 3,080 rows), same duplicate-text filter as main; additionally excluded every
  text (normalised) appearing in `items.jsonl` or `pilot.jsonl`. Candidate pool after exclusion: {pool} rows.
- Sampling: stratified by intent. Every one of the 77 intents gets {base}; {extra} distinct intents chosen at random
  get one more ({base + 1}). Rows sampled uniformly within intent; order shuffled.
- Count: {len(confirm)}. Distribution: {per_label.get(base, 0)} intents × {base}, {per_label.get(base + 1, 0)} intents × {base + 1}.
- Disjoint from main and pilot by `id` and by normalised text.
""")
    return {"confirm": len(confirm), "dist": dict(per_label), "pool": pool}


BLIMP_CONFIRM_OFFSET = BLIMP_ROWS_PER_PARADIGM  # rows 100.. of each paradigm (main/pilot used rows 0-99)
BLIMP_CONFIRM_ROWS = 100  # rows 100-199


def confirm_blimp() -> dict:
    rng = random.Random(CONFIRM_SEED)
    raw = RAW / "blimp"
    paradigms, human, _ = _blimp_meta()
    used = used_items("blimp")
    used_ids = {i["id"] for i in used}
    used_sents = {norm_text(s[3:]) for i in used for s in i["input"].split("\n")}

    base = N_CONFIRM // len(paradigms)  # 8
    extra = N_CONFIRM - base * len(paradigms)  # 64
    extra_set = set(rng.sample(paradigms, extra))
    rows, pool_sizes = [], {}
    for p in paradigms:
        cands = [x["row"] for x in hf_rows(BLIMP_DS, p, "train", BLIMP_CONFIRM_OFFSET, BLIMP_CONFIRM_ROWS, raw / p)]
        # exclude pairs used before, pairs sharing any sentence with main/pilot, and pairs sharing a
        # sentence with an earlier candidate (so confirm items are mutually sentence-disjoint too)
        ok, seen = [], set(used_sents)
        for r in cands:
            sg, sb = norm_text(r["sentence_good"]), norm_text(r["sentence_bad"])
            if f"blimp-{p}-{r['pair_id']}" in used_ids or sg in seen or sb in seen or sg == sb:
                continue
            seen.update({sg, sb})
            ok.append(r)
        pool_sizes[p] = len(ok)
        k = base + (p in extra_set)
        assert len(ok) >= k, (p, len(ok))
        rows.extend((p, r) for r in rng.sample(ok, k))
    rng.shuffle(rows)
    golds = ["A"] * (N_CONFIRM // 2) + ["B"] * (N_CONFIRM - N_CONFIRM // 2)
    rng.shuffle(golds)
    confirm = [_blimp_item(p, r, g, human) for (p, r), g in zip(rows, golds)]
    _check_disjoint("blimp", confirm, used)
    conf_sents = [norm_text(s[3:]) for i in confirm for s in i["input"].split("\n")]
    assert not set(conf_sents) & used_sents

    out = TASKS / "blimp"
    write_jsonl(out / "confirm.jsonl", confirm)
    ga = Counter(i["gold"] for i in confirm)
    per_p = Counter(Counter(i["meta"]["paradigm"] for i in confirm).values())
    fields = Counter(i["meta"]["field"] for i in confirm)
    n_h = sum("human_ref" in i for i in confirm)
    lo, hi = BLIMP_CONFIRM_OFFSET, BLIMP_CONFIRM_OFFSET + BLIMP_CONFIRM_ROWS - 1
    set_confirm_section(out / "SOURCE.md", f"""{CONFIRM_HEADING} (`confirm.jsonl`)
- Purpose: {N_CONFIRM} fresh items to confirm findings made on the 200 main items. Built with
  `PYTHONPATH=src python -m gch.build_tasks --confirm` (does not touch `items.jsonl` / `pilot.jsonl`).
- **Seed:** {CONFIRM_SEED} (`random.Random(CONFIRM_SEED)`, see `src/gch/build_tasks.py::confirm_blimp`)
- Source rows: for each of the 67 paradigms, pairs at rows {lo}–{hi} (of 1000), i.e. entirely outside the
  rows 0–{BLIMP_ROWS_PER_PARADIGM - 1} pool used for main/pilot (one extra datasets-server page per paradigm,
  cached as `tasks/_raw/blimp/<paradigm>/train_{lo:08d}_{BLIMP_CONFIRM_ROWS}.json`).
- Filters: dropped any pair whose id is in main/pilot or whose good/bad sentence (normalised) appears in any
  main/pilot item, and any pair sharing a sentence with an earlier candidate in the same paradigm
  (confirm items are mutually sentence-disjoint). Candidates per paradigm after filtering:
  {min(pool_sizes.values())}–{max(pool_sizes.values())}.
- Sampling: stratified across paradigms: {base} pairs each, plus one more for {extra} paradigms chosen at random →
  {per_p.get(base, 0)} paradigms × {base}, {per_p.get(base + 1, 0)} paradigms × {base + 1}. Order shuffled.
- A/B order: exactly balanced, assignment shuffled with the seed. Gold balance: A = {ga["A"]}, B = {ga["B"]}.
- Field distribution: {", ".join(f"{k} {v}" for k, v in sorted(fields.items()))}.
- Human agreement attached exactly as for main (`human_ref` + `meta.human_agreement`, per paradigm): {n_h}/{len(confirm)} items.
- Count: {len(confirm)}.
""")
    return {"confirm": len(confirm), "AB": dict(ga), "per_paradigm": dict(per_p),
            "pool_min": min(pool_sizes.values())}


CC_CONFIRM_MAX = 20000  # bound on how far into the test split the confirm build may page
CC_CONFIRM_STEP = 2000


def confirm_toxicity() -> dict:
    rng = random.Random(CONFIRM_SEED)
    used = used_items("toxicity")
    used_ids = {i["id"] for i in used}
    used_norm = {norm_text(i["input"]) for i in used}
    n_yes = round(N_CONFIRM * 0.3)  # 180
    n_no = N_CONFIRM - n_yes  # 420

    n_rows = CC_TEST_SLICE
    while True:
        pool = [r for r in _cc_load("test", 0, n_rows)
                if norm_text(r["text"]) not in used_norm and f"toxicity-test-{r['row']:06d}" not in used_ids]
        yes = [r for r in pool if r["toxicity"] >= 0.5]
        no = [r for r in pool if r["toxicity"] < 0.5]
        if len(yes) >= n_yes and len(no) >= n_no:
            break
        assert n_rows < CC_CONFIRM_MAX, (n_rows, len(yes), len(no))
        n_rows = min(CC_CONFIRM_MAX, n_rows + CC_CONFIRM_STEP)
    rows = rng.sample(yes, n_yes) + rng.sample(no, n_no)
    rng.shuffle(rows)
    confirm = [_cc_item(r, "test") for r in rows]
    _check_disjoint("toxicity", confirm, used)

    out = TASKS / "toxicity"
    write_jsonl(out / "confirm.jsonl", confirm)
    g = Counter(i["gold"] for i in confirm)
    set_confirm_section(out / "SOURCE.md", f"""{CONFIRM_HEADING} (`confirm.jsonl`) — test split
- Purpose: {N_CONFIRM} fresh items to confirm findings made on the 200 main items. Built with
  `PYTHONPATH=src python -m gch.build_tasks --confirm` (does not touch `items.jsonl` / `pilot.jsonl`).
- **Seed:** {CONFIRM_SEED} (`random.Random(CONFIRM_SEED)`, see `src/gch/build_tasks.py::confirm_toxicity`)
- Source rows: test split rows 0–{n_rows - 1} (same cached datasets-server pages as main; the builder pages further,
  up to row {CC_CONFIRM_MAX - 1}, only if this pool is too small). Same filters as main (20–600 chars,
  normalised duplicates dropped); additionally excluded every main/pilot id and every text (normalised)
  appearing in `items.jsonl` or `pilot.jsonl`. Pool after exclusion: {len(yes)} YES / {len(no)} NO.
- Sampling: stratified random sample, exactly {n_yes} YES + {n_no} NO (30% toxic, same ratio as main). Order shuffled.
- Count: {len(confirm)} (YES {g["YES"]}, NO {g["NO"]}). Raw score kept in `meta.toxicity`.
- Disjoint from main and pilot by `id` and by normalised text.
""")
    return {"confirm": len(confirm), "dist": dict(g), "rows": n_rows, "pool": (len(yes), len(no))}


def main(argv: list[str] | None = None) -> None:
    import argparse

    ap = argparse.ArgumentParser(prog="python -m gch.build_tasks")
    ap.add_argument("--confirm", action="store_true",
                    help="build only tasks/<task>/confirm.jsonl (items.jsonl/pilot.jsonl untouched)")
    args = ap.parse_args(argv)
    TASKS.mkdir(exist_ok=True)
    summary = {}
    if args.confirm:
        steps = (("banking77", confirm_banking77), ("blimp", confirm_blimp), ("toxicity", confirm_toxicity))
    else:
        steps = (("banking77", build_banking77), ("blimp", build_blimp), ("toxicity", build_toxicity))
    for name, fn in steps:
        print(f"[build_tasks] building {name}{' confirm' if args.confirm else ''} ...", flush=True)
        summary[name] = fn()
        print(f"[build_tasks] {name}: {summary[name]}", flush=True)


if __name__ == "__main__":
    main()

"""Sanity checks on the built task packs (run `python -m gch.build_tasks` first)."""

import json
from collections import Counter
from pathlib import Path

import pytest
import yaml

TASKS = Path(__file__).resolve().parents[1] / "tasks"
TASK_IDS = ["banking77", "blimp", "toxicity"]
REQUIRED_YAML = {"name", "task_id", "answer_type", "instructions", "target_precision",
                 "target_accuracy", "licence", "source_url"}


def norm(s: str) -> str:
    return " ".join(s.casefold().split())


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_task(tid: str):
    d = TASKS / tid
    cfg = yaml.safe_load((d / "task.yaml").read_text(encoding="utf-8"))
    if "options_file" in cfg:
        options = [l for l in (d / cfg["options_file"]).read_text(encoding="utf-8").splitlines() if l]
    else:
        options = cfg["options"]
    return cfg, options, load_jsonl(d / "items.jsonl"), load_jsonl(d / "pilot.jsonl")


@pytest.mark.parametrize("tid", TASK_IDS)
def test_task_pack(tid):
    cfg, options, main, pilot = load_task(tid)
    assert REQUIRED_YAML <= set(cfg)
    assert cfg["task_id"] == tid
    assert cfg["answer_type"] in {"single_choice", "binary", "probability"}
    assert cfg["target_precision"] == 0.95
    assert (TASKS / tid / "SOURCE.md").exists()
    assert len(options) == len(set(options))

    assert len(main) == 200 and len(pilot) == 10
    for it in main + pilot:
        assert set(it) >= {"id", "input", "gold", "meta"}
        assert isinstance(it["id"], str) and isinstance(it["input"], str) and it["input"].strip()
        assert isinstance(it["meta"], dict)
        assert it["gold"] in options

    main_ids, pilot_ids = [i["id"] for i in main], [i["id"] for i in pilot]
    assert len(set(main_ids)) == 200 and len(set(pilot_ids)) == 10
    assert not set(main_ids) & set(pilot_ids)
    main_txt = {norm(i["input"]) for i in main}
    assert len(main_txt) == 200
    assert not main_txt & {norm(i["input"]) for i in pilot}


def test_banking77_specifics():
    _, options, main, _ = load_task("banking77")
    assert len(options) == 77
    c = Counter(i["gold"] for i in main)
    assert set(c) == set(options) and min(c.values()) >= 2 and max(c.values()) <= 3


def test_blimp_specifics():
    _, _, main, pilot = load_task("blimp")
    assert len({i["meta"]["paradigm"] for i in main}) == 67
    assert Counter(i["gold"] for i in main) == {"A": 100, "B": 100}
    main_sents = {norm(s[3:]) for i in main for s in i["input"].split("\n")}
    for i in main + pilot:
        assert i["input"].startswith("A: ") and "\nB: " in i["input"]
    for i in pilot:
        assert not {norm(s[3:]) for s in i["input"].split("\n")} & main_sents


def test_toxicity_specifics():
    cfg, _, main, pilot = load_task("toxicity")
    assert cfg["options"] == ["YES", "NO"]
    assert Counter(i["gold"] for i in main) == {"YES": 60, "NO": 140}
    assert Counter(i["gold"] for i in pilot) == {"YES": 3, "NO": 7}
    for i in main + pilot:
        assert 20 <= len(i["input"]) <= 600
        assert (i["meta"]["toxicity"] >= 0.5) == (i["gold"] == "YES")

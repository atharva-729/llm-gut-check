import numpy as np
import pytest

from gch import metrics, threshold, verdict
from gch.models import MODELS
from gch.parse import parse_answer

OPTS = ["card_arrival", "card_linking", "YES", "NO"]


# ---------- parse
@pytest.mark.parametrize("text,ans,conf", [
    ('{"answer": "card_arrival", "confidence": 80}', "card_arrival", 80),
    ('```json\n{"answer":"Card_Arrival","confidence":"75%"}\n```', "card_arrival", 75),
    ('Sure! {"answer": "YES", "confidence": 0.9}', "YES", 90),
    ('{"answer": "NO", "confidence": 1}', "NO", 1),
])
def test_parse_ok(text, ans, conf):
    p = parse_answer(text, OPTS)
    assert p.ok and p.answer == ans and p.confidence == pytest.approx(conf)


@pytest.mark.parametrize("text,reason", [
    ("no json here", "no_json"),
    ('{"answer": "maybe", "confidence": 50}', "answer_not_in_options"),
    ('{"answer": "YES", "confidence": 150}', "confidence_out_of_range"),
    ('{"confidence": 50}', "no_answer_field"),
])
def test_parse_fail(text, reason):
    p = parse_answer(text, OPTS)
    assert not p.ok and p.reason.startswith(reason)


# ---------- cost
def test_cost_openai():
    m = MODELS["gpt-5.4-mini"]
    usd = m.cost({"input": 1_000_000, "cached_input": 0, "output": 1_000_000})
    assert usd == pytest.approx(m.price_in + m.price_out)


def test_cost_cached_discount():
    m = MODELS["claude-haiku-4-5"]
    assert m.cost({"input": 1000, "cached_input": 1000, "output": 0}) < m.cost({"input": 1000, "output": 0})


# ---------- metrics
def r(correct, conf=90, ans=None, status="ok"):
    return {"correct": correct, "confidence": conf, "answer": ans, "status": status}


def test_accuracy_and_parse_fail_counts_wrong():
    rows = [r(True)] * 8 + [r(None, None, status="parse_fail")] * 2
    a = metrics.accuracy(rows)
    assert a["acc"] == pytest.approx(0.8) and a["ci"][0] <= 0.8 <= a["ci"][1]


def test_ece_perfect_and_bad():
    conf = np.array([0.95] * 100)
    assert metrics.ece(conf, np.array([1.0] * 95 + [0.0] * 5)) == pytest.approx(0.0, abs=1e-9)
    assert metrics.ece(conf, np.array([1.0] * 50 + [0.0] * 50)) == pytest.approx(0.45)


def test_flips():
    gut = {"a": r(True, ans="x"), "b": r(False, ans="y"), "c": r(False, ans="y"), "d": r(True, ans="x")}
    rea = {"a": r(False, ans="z"), "b": r(True, ans="x"), "c": r(False, ans="w"), "d": r(True, ans="x")}
    f = metrics.flips(gut, rea)
    assert (f["right_to_wrong"], f["wrong_to_right"], f["wrong_to_wrong_changed"], f["unchanged"]) == (1, 1, 1, 1)
    assert f["overthinking_share_of_flips"] == pytest.approx(1 / 3)


# ---------- threshold
def test_wilson_known_value():
    # 95/100 -> Wilson 95% lower bound ~0.8882
    assert threshold.wilson_lower(95, 100) == pytest.approx(0.8882, abs=1e-3)


def test_min_n_for_99_and_95():
    assert threshold.min_all_correct_n(0.99) > 300
    assert 70 <= threshold.min_all_correct_n(0.95) <= 80


def test_search_finds_lowest_safe_threshold():
    rows = [r(True, 95)] * 100 + [r(False, 60)] * 50 + [r(True, 60)] * 50
    th = threshold.search(rows, 0.95)
    assert th["found"] and th["threshold"] == 95 and th["coverage"] == pytest.approx(0.5)


def test_search_none_when_too_few():
    rows = [r(True, 99)] * 20 + [r(False, 50)] * 180
    assert not threshold.search(rows, 0.95)["found"]


# ---------- verdict
def test_fast_when_ci_includes_zero():
    v = verdict.mode_choice({"diff": 0.03, "ci": [-0.01, 0.07]}, 1.0, 5.0, 200)
    assert v["verdict"] == "Use fast mode"


def test_fast_when_gain_tiny():
    assert verdict.mode_choice({"diff": 0.005, "ci": [0.001, 0.01]}, 1, 5, 200)["verdict"] == "Use fast mode"


def test_reasoning_with_cost_per_extra_correct():
    v = verdict.mode_choice({"diff": 0.10, "ci": [0.05, 0.15]}, 1.0, 11.0, 200)
    assert v["verdict"] == "Use reasoning" and v["cost_per_extra_correct_usd"] == pytest.approx(0.1)


def test_overthinking_flag():
    assert verdict.overthinking({"overthinking_rate": 0.04, "flips": 10, "overthinking_share_of_flips": 0.1})
    assert verdict.overthinking({"overthinking_rate": 0.01, "flips": 10, "overthinking_share_of_flips": 0.3})
    assert not verdict.overthinking({"overthinking_rate": 0.01, "flips": 10, "overthinking_share_of_flips": 0.2})


def test_cheapest():
    cfgs = [
        {"model": "a", "mode": "gut", "cost_per_1k": 1, "acc_ci_lo": 0.85, "threshold": {"found": True, "coverage": 0.6}},
        {"model": "a", "mode": "reasoned", "cost_per_1k": 5, "acc_ci_lo": 0.92, "threshold": {"found": True, "coverage": 0.8}},
        {"model": "b", "mode": "reasoned", "cost_per_1k": 9, "acc_ci_lo": 0.95, "threshold": {"found": False}},
    ]
    for c in cfgs:
        c["threshold"].setdefault("threshold", 90)
    ch = verdict.cheapest(cfgs, 0.90)
    assert ch["by_accuracy"]["cost_per_1k"] == 5 and ch["by_auto_accept"]["coverage"] == 0.8

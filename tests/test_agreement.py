import pytest

from gch import agreement as ag

G, H, M = "gpt-5.4-mini", "claude-haiku-4-5", "gemini-3.5-flash"


def cell(ans, conf, gold="A", cost=0.001, status="ok"):
    return {"answer": ans, "confidence": conf, "gold": gold, "correct": ans == gold, "status": status,
            "cost_usd": cost}


def item(g, h, m, gold="A", mode="gut"):
    return {(G, mode): cell(*g, gold=gold), (H, mode): cell(*h, gold=gold), (M, mode): cell(*m, gold=gold)}


P_SELF = {"kind": "SELF", "models": (G,), "mode": "gut"}
P_AGREE = {"kind": "AGREE", "models": (G, H), "mode": "gut"}
P_ALL = {"kind": "AGREE", "models": (G, H, M), "mode": "gut"}
P_MAJ = {"kind": "MAJ", "models": (G, H, M), "mode": "gut"}


def test_decide_self_and_agree():
    cells = item(("A", 90), ("A", 80), ("B", 99))
    assert ag.decide(P_SELF, cells, 85) == "A"
    assert ag.decide(P_AGREE, cells, 80) == "A"
    assert ag.decide(P_AGREE, cells, 85) is None      # haiku below floor
    assert ag.decide(P_ALL, cells, 0) is None         # gemini disagrees
    assert ag.decide(P_MAJ, cells, 80) == "A"         # 2 of 3, both >= 80
    assert ag.decide(P_MAJ, cells, 85) is None        # an agreeing model is below floor


def test_maj_no_majority():
    assert ag.decide(P_MAJ, item(("A", 99), ("B", 99), ("C", 99)), 0) is None


def test_parse_fail_never_accepted():
    cells = item(("A", 90), ("A", 90), ("A", 90))
    cells[(H, "gut")]["status"] = "parse_fail"
    assert ag.decide(P_AGREE, cells, 0) is None
    assert ag.decide(P_MAJ, cells, 0) == "A"  # gpt+gemini still a majority


def test_evaluate_and_costs():
    items = {"1": item(("A", 90), ("A", 90), ("A", 90)), "2": item(("B", 90), ("B", 90), ("A", 90)),
             "3": item(("A", 40), ("A", 90), ("A", 90)), "4": item(("A", 90), ("B", 90), ("A", 90))}
    e = ag.evaluate(P_AGREE, items, 50)
    assert (e["accepted"], e["correct"]) == (2, 1)
    assert e["coverage"] == 0.5 and e["api_cost_per_1k"] == pytest.approx(2.0)
    # total = api 2.0 + review 0.25*2/4*1000 + error 2.5*1/4*1000
    assert ag.total_cost_per_1k(e) == pytest.approx(2.0 + 125 + 625)


def test_fit_picks_lowest_floor_meeting_97():
    items = {}
    for i in range(40):
        items[f"hi{i}"] = item(("A", 95), ("A", 95), ("A", 95))
    for i in range(10):
        items[f"lo{i}"] = item(("B", 60), ("B", 60), ("B", 60))  # wrong, low confidence
    assert ag.fit(P_AGREE, items) == 70


def test_h4_logic():
    rows = [
        {"policy": "s", "kind": "SELF", "mode": "reasoned", "passes": True, "coverage": 0.7, "api_cost_per_1k": 2.5},
        {"policy": "a", "kind": "AGREE", "mode": "gut", "passes": True, "coverage": 0.74, "api_cost_per_1k": 0.6},
        {"policy": "r", "kind": "AGREE", "mode": "reasoned", "passes": True, "coverage": 0.9, "api_cost_per_1k": 4},
    ]
    r = ag.h4(rows)
    assert r["holds"] and r["best_gut_agree"] == "a" and r["best_self"] == "s"
    rows[1]["coverage"] = 0.6
    assert not ag.h4(rows)["holds"]


def test_policy_count():
    assert len(ag.make_policies([G, H, M])) == 6 + 2 * (3 + 1 + 1)

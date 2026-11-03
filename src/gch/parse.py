"""Parse model output into {answer, confidence}."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass


@dataclass
class Parsed:
    ok: bool
    answer: str | None = None
    confidence: float | None = None   # 0-100
    reason: str | None = None


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip().strip("\"'.").lower()


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        d = json.loads(text)
        return d if isinstance(d, dict) else None
    except json.JSONDecodeError:
        pass
    # last {...} object in the text
    for m in reversed(list(re.finditer(r"\{[^{}]*\}", text, re.S))):
        try:
            d = json.loads(m.group(0))
            if isinstance(d, dict):
                return d
        except json.JSONDecodeError:
            continue
    return None


def parse_answer(text: str, options: list[str]) -> Parsed:
    d = _extract_json(text or "")
    if d is None:
        return Parsed(False, reason="no_json")
    if "answer" not in d:
        return Parsed(False, reason="no_answer_field")
    lookup = {_norm(o): o for o in options}
    ans = lookup.get(_norm(d["answer"]))
    if ans is None:
        return Parsed(False, reason=f"answer_not_in_options:{str(d['answer'])[:60]}")
    conf = d.get("confidence")
    try:
        conf = float(str(conf).rstrip("%"))
    except (TypeError, ValueError):
        return Parsed(False, answer=ans, reason="bad_confidence")
    if 0 < conf <= 1 and not float(conf).is_integer():
        conf *= 100  # model answered on a 0-1 scale
    if not 0 <= conf <= 100:
        return Parsed(False, answer=ans, reason="confidence_out_of_range")
    return Parsed(True, answer=ans, confidence=conf)

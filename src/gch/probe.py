"""`gch probe`: 3 tiny calls per model per mode; checks mode acceptance, reasoning leak, JSON support, latency."""
from __future__ import annotations

import json
from pathlib import Path

from . import llm
from .models import MODELS
from .parse import parse_answer

PROBES = [
    ("Is 91 a prime number?", "NO"),
    ("Is the sentence 'The cats sleeps on the mat.' grammatical?", "NO"),
    ("Is Paris the capital of France?", "YES"),
]
SYSTEM = ("Answer the yes/no question. Respond only with JSON: "
          '{"answer": "YES" or "NO", "confidence": integer 0-100 = probability your answer is correct}.')
SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string", "enum": ["YES", "NO"]}, "confidence": {"type": "integer"}},
    "required": ["answer", "confidence"],
    "additionalProperties": False,
}


def run(models: list[str], out: Path) -> list[dict]:
    rows = []
    for key in models:
        m = MODELS[key]
        for mode in m.modes:
            for use_schema in (True, False):
                res = []
                for q, gold in PROBES:
                    r = llm.call(m, mode, SYSTEM, q, SCHEMA if use_schema else None, use_cache=False)
                    p = parse_answer(r.get("text", ""), ["YES", "NO"]) if not r.get("error") else None
                    res.append((r, p, gold))
                errs = [r["error"] for r, _, _ in res if r.get("error")]
                ok = [r for r, _, _ in res if not r.get("error")]
                row = {
                    "model": key, "mode": mode, "structured_output": use_schema,
                    "accepted": not errs,
                    "error": errs[0][:300] if errs else None,
                    "reasoning_tokens": [r["usage"].get("reasoning") for r in ok],
                    "reasoning_measured": ok[0]["usage"].get("reasoning_measured") if ok else None,
                    "output_tokens": [r["usage"].get("output") for r in ok],
                    "json_ok": sum(1 for _, p, _ in res if p and p.ok),
                    "correct": sum(1 for _, p, g in res if p and p.ok and p.answer == g),
                    "latency_s": [r.get("latency_s") for r in ok],
                    "cost_usd": round(sum(r.get("cost_usd", 0) for r in ok), 6),
                    "sample": (ok[0].get("text", "")[:160] if ok else None),
                }
                rows.append(row)
                print(json.dumps(row))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return rows

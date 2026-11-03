"""OpenAI-compatible LLM gateway clients (OpenAI + Anthropic routes) with mode controls, usage capture and a disk cache."""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

from .models import Model

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "runs" / "cache"
load_dotenv(ROOT / ".env")

APP = "gut-check-harness"
_client: httpx.Client | None = None


def _http() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(timeout=httpx.Timeout(180.0, connect=20.0))
    return _client


def _base() -> str:
    return os.environ.get("LLM_API_BASE", "").rstrip("/")


def _auth() -> str:
    tok = os.environ.get("LLM_API_TOKEN")
    if not tok:
        raise RuntimeError("LLM_API_TOKEN not set (put it in .env)")
    return f"Bearer {tok}:{APP}"


def cache_key(model: Model, mode: str, system: str, user: str, schema: dict | None, attempt: int) -> str:
    blob = json.dumps(
        {"m": model.model_id, "mode": mode, "params": model.modes[mode], "s": system, "u": user,
         "schema": schema, "a": attempt},
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


# ---------------------------------------------------------------- providers
def _openai(model: Model, mode: str, system: str, user: str, schema: dict | None) -> tuple[dict, dict]:
    body = {
        "model": model.model_id,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        **model.modes[mode],
    }
    if schema:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "answer", "strict": True, "schema": schema},
        }
    r = _http().post(f"{_base()}/openai/v1/chat/completions", json=body, headers={"Authorization": _auth()})
    _raise(r)
    d = r.json()
    u = d.get("usage", {}) or {}
    usage = {
        "input": u.get("prompt_tokens", 0),
        "cached_input": (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0) or 0,
        "output": u.get("completion_tokens", 0),
        "reasoning": (u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0) or 0,
        "reasoning_measured": True,
    }
    text = d["choices"][0]["message"].get("content") or ""
    return {"text": text, "finish": d["choices"][0].get("finish_reason")}, usage


def _anthropic(model: Model, mode: str, system: str, user: str, schema: dict | None) -> tuple[dict, dict]:
    body = {
        "model": model.model_id,
        "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": user}],
        **model.modes[mode],
    }
    if schema:
        body["output_config"] = {"format": {"type": "json_schema", "schema": schema}}
    r = _http().post(
        f"{_base()}/anthropic/v1/messages",
        json=body,
        headers={"Authorization": _auth(), "anthropic-version": "2023-06-01"},
    )
    _raise(r)
    d = r.json()
    text = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
    thinking = "".join(b.get("thinking", "") for b in d.get("content", []) if b.get("type") == "thinking")
    has_thinking = any(b.get("type") in ("thinking", "redacted_thinking") for b in d.get("content", []))
    u = d.get("usage", {}) or {}
    out = u.get("output_tokens", 0)
    cached = u.get("cache_read_input_tokens", 0) or 0
    write = u.get("cache_creation_input_tokens", 0) or 0
    # Anthropic does not report thinking tokens separately: estimate = output minus visible answer.
    reasoning = max(0, out - math.ceil(len(text) / 3.5)) if has_thinking else 0
    usage = {
        "input": (u.get("input_tokens", 0) or 0) + cached + write,
        "cached_input": cached,
        "cache_write": write,
        "output": out,
        "reasoning": reasoning,
        "reasoning_measured": False,
    }
    return {"text": text, "finish": d.get("stop_reason"), "thinking_chars": len(thinking),
            "has_thinking": has_thinking}, usage


def _gemini(model: Model, mode: str, system: str, user: str, schema: dict | None) -> tuple[dict, dict]:
    p = model.modes[mode]
    gen = {"maxOutputTokens": p.get("max_tokens", 8000)}
    if "thinking" in p:
        gen["thinkingConfig"] = p["thinking"]
    if schema:
        gen["responseMimeType"] = "application/json"
        gen["responseJsonSchema"] = schema
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": gen,
    }
    r = _http().post(f"{_base()}/gemini/v1beta/models/{model.model_id}:generateContent", json=body,
                     headers={"Authorization": _auth()})
    _raise(r)
    d = r.json()
    cand = (d.get("candidates") or [{}])[0]
    parts = (cand.get("content") or {}).get("parts") or []
    text = "".join(pt.get("text", "") for pt in parts if not pt.get("thought"))
    u = d.get("usageMetadata", {}) or {}
    thoughts = u.get("thoughtsTokenCount", 0) or 0
    usage = {
        "input": u.get("promptTokenCount", 0) or 0,
        "cached_input": u.get("cachedContentTokenCount", 0) or 0,
        "output": (u.get("candidatesTokenCount", 0) or 0) + thoughts,  # thinking is billed as output
        "reasoning": thoughts,
        "reasoning_measured": True,
    }
    return {"text": text, "finish": cand.get("finishReason")}, usage


class APIError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body[:500]}")
        self.status = status
        self.body = body


def _raise(r: httpx.Response) -> None:
    if r.status_code >= 400:
        raise APIError(r.status_code, r.text)


PROVIDERS = {"openai": _openai, "anthropic": _anthropic, "gemini": _gemini}


# ---------------------------------------------------------------- public
def call(model: Model, mode: str, system: str, user: str, schema: dict | None = None,
         attempt: int = 0, use_cache: bool = True, max_tries: int = 6) -> dict:
    """Return {text, usage, latency_s, cost_usd, cached, error?}. Never raises on API errors after retries."""
    key = cache_key(model, mode, system, user, schema, attempt)
    path = CACHE_DIR / f"{key}.json"
    if use_cache and path.exists():
        rec = json.loads(path.read_text(encoding="utf-8"))
        rec["from_cache"] = True
        return rec

    fn = PROVIDERS[model.provider]
    last_err = None
    for i in range(max_tries):
        t0 = time.perf_counter()
        try:
            resp, usage = fn(model, mode, system, user, schema)
            rec = {
                "model": model.key, "mode": mode, **resp, "usage": usage,
                "latency_s": round(time.perf_counter() - t0, 3),
                "cost_usd": model.cost(usage), "ts": time.time(),
            }
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(rec), encoding="utf-8")
            rec["from_cache"] = False
            return rec
        except APIError as e:
            last_err = str(e)
            if e.status not in (408, 409, 429, 500, 502, 503, 504, 529):
                break
        except (httpx.TransportError, httpx.TimeoutException) as e:
            last_err = f"{type(e).__name__}: {e}"
        time.sleep(min(60, 2 ** i + random.random() * 2))
    return {"model": model.key, "mode": mode, "error": last_err, "text": "", "usage": {}, "cost_usd": 0.0,
            "latency_s": None, "from_cache": False}

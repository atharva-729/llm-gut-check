"""Model registry: gateway model IDs, prices, mode settings, and where each fact came from."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Model:
    key: str                 # name used in config / reports
    provider: str            # openai | anthropic
    model_id: str            # exact ID sent to the gateway
    price_in: float          # USD per 1M uncached input tokens
    price_cached_in: float   # USD per 1M cached input tokens (cache read)
    price_out: float         # USD per 1M output tokens (includes reasoning/thinking)
    price_source: str
    cutoff: str | None       # training cutoff (only needed for forecasting tasks)
    modes: dict = field(default_factory=dict)  # mode -> provider params
    notes: str = ""

    def cost(self, usage: dict) -> float:
        cached = usage.get("cached_input", 0) or 0
        uncached = max(0, (usage.get("input", 0) or 0) - cached)
        cache_write = usage.get("cache_write", 0) or 0
        return (
            uncached * self.price_in
            + cached * self.price_cached_in
            + cache_write * self.price_in * 0.25  # Anthropic cache writes cost 1.25x input; 1x already counted
            + (usage.get("output", 0) or 0) * self.price_out
        ) / 1e6


MODELS: dict[str, Model] = {
    "gpt-5.4-mini": Model(
        key="gpt-5.4-mini",
        provider="openai",
        model_id="gpt-5.4-mini",
        price_in=0.75,
        price_cached_in=0.075,
        price_out=4.50,
        price_source="input $0.75 confirmed in sibling project l1l2l3 (config.yaml); output $4.50 and cached $0.075 ASSUMED — verify",
        cutoff=None,
        modes={
            "gut": {"reasoning_effort": "none", "max_completion_tokens": 400},
            "reasoned": {"reasoning_effort": "medium", "max_completion_tokens": 16000},
        },
    ),
    "claude-haiku-4-5": Model(
        key="claude-haiku-4-5",
        provider="anthropic",
        model_id="claude-haiku-4-5-20251001",
        price_in=1.00,
        price_cached_in=0.10,
        price_out=5.00,
        price_source="Anthropic first-party list price (claude-api reference, cached 2026-10-06)",
        cutoff=None,
        modes={
            "gut": {"max_tokens": 400},
            "reasoned": {"max_tokens": 6000, "thinking": {"type": "enabled", "budget_tokens": 2048}},
        },
        notes="Prompt caching needs >=4096-token prefix on Haiku 4.5, so option lists here will not cache.",
    ),
}


def get(key: str) -> Model:
    if key not in MODELS:
        raise KeyError(f"unknown model {key!r}; known: {sorted(MODELS)}")
    return MODELS[key]

"""Load task packs and render prompts (same template for every task; only the task block changes)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TASKS_DIR = ROOT / "tasks"
TEMPLATE = (ROOT / "prompts" / "system.md").read_text(encoding="utf-8")


@dataclass
class Task:
    task_id: str
    name: str
    answer_type: str
    options: list[str]
    instructions: str
    target_precision: float
    target_accuracy: float
    cfg: dict

    @property
    def system_prompt(self) -> str:
        opts = "\n".join(f"- {o}" for o in self.options)
        block = f"Allowed answers ({len(self.options)}):\n{opts}"
        return (TEMPLATE.replace("{task_name}", self.name)
                .replace("{instructions}", self.instructions.strip())
                .replace("{options_block}", block))

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "answer": {"type": "string", "enum": self.options},
                "confidence": {"type": "integer"},
            },
            "required": ["answer", "confidence"],
            "additionalProperties": False,
        }

    def items(self, split: str = "main") -> list[dict]:
        fn = "items.jsonl" if split == "main" else "pilot.jsonl"
        return _read_jsonl(TASKS_DIR / self.task_id / fn)


def _read_jsonl(p: Path) -> list[dict]:
    with p.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


@lru_cache(maxsize=None)
def load(task_id: str) -> Task:
    d = TASKS_DIR / task_id
    cfg = yaml.safe_load((d / "task.yaml").read_text(encoding="utf-8"))
    if cfg.get("options_file"):
        options = [l.strip() for l in (d / cfg["options_file"]).read_text(encoding="utf-8").splitlines() if l.strip()]
    else:
        options = [str(o) for o in cfg["options"]]
    return Task(
        task_id=task_id,
        name=cfg.get("name", task_id),
        answer_type=cfg["answer_type"],
        options=options,
        instructions=cfg["instructions"],
        target_precision=float(cfg.get("target_precision", 0.95)),
        target_accuracy=float(cfg.get("target_accuracy", 0.9)),
        cfg=cfg,
    )

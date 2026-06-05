"""Append-only JSONL telemetry for latency and LLM token cost.

Every scoring call and every LLM credit-memo call writes one line, so the
monitoring dashboard can report p50/p95 latency and cumulative spend — a named
2026 employer expectation (cost + observability).
"""
from __future__ import annotations
import json, time, threading
from pathlib import Path
from typing import Optional

_LOCK = threading.Lock()

# Indicative prices (USD per 1K tokens); override via config as needed.
PRICE_PER_1K = {"gpt-4o-mini": {"in": 0.00015, "out": 0.0006},
                "claude-3-5-haiku": {"in": 0.0008, "out": 0.004}}


def estimate_cost(model: str, in_tokens: int, out_tokens: int) -> float:
    p = PRICE_PER_1K.get(model, {"in": 0.0, "out": 0.0})
    return round(in_tokens / 1000 * p["in"] + out_tokens / 1000 * p["out"], 6)


def log_event(path: Path, event: str, latency_ms: float,
              model: Optional[str] = None, in_tokens: int = 0,
              out_tokens: int = 0, extra: Optional[dict] = None) -> None:
    rec = {
        "ts": time.time(),
        "event": event,
        "latency_ms": round(latency_ms, 2),
        "model": model,
        "in_tokens": in_tokens,
        "out_tokens": out_tokens,
        "cost_usd": estimate_cost(model, in_tokens, out_tokens) if model else 0.0,
        **(extra or {}),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        with open(path, "a") as f:
            f.write(json.dumps(rec) + "\n")

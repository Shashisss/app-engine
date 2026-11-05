"""Spend guard for the model: a simple hourly and daily call budget.

Every model call costs someone money, and the engine is reachable over a public
tunnel, so the budget is counted in a small JSON file next to the registry.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "apps" / "llm_budget.json"

HOURLY = int(os.getenv("APP_ENGINE_LLM_HOURLY", "40"))
DAILY = int(os.getenv("APP_ENGINE_LLM_DAILY", "200"))


def _load() -> list[float]:
    if not STATE.exists():
        return []
    try:
        data = json.loads(STATE.read_text())
        return [float(t) for t in data if isinstance(t, (int, float))]
    except (json.JSONDecodeError, TypeError, ValueError):
        return []


def _save(stamps: list[float]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(stamps[-500:]))


def _prune(stamps: list[float]) -> list[float]:
    cutoff = time.time() - 24 * 3600
    return [t for t in stamps if t >= cutoff]


def usage() -> dict[str, int]:
    stamps = _prune(_load())
    hour_ago = time.time() - 3600
    return {
        "last_hour": sum(1 for t in stamps if t >= hour_ago),
        "last_day": len(stamps),
        "hourly_limit": HOURLY,
        "daily_limit": DAILY,
    }


def allowed() -> tuple[bool, str]:
    current = usage()
    if current["last_hour"] >= HOURLY:
        return False, f"hourly model budget reached ({HOURLY}/hour)"
    if current["last_day"] >= DAILY:
        return False, f"daily model budget reached ({DAILY}/day)"
    return True, ""


def record() -> None:
    stamps = _prune(_load())
    stamps.append(time.time())
    _save(stamps)

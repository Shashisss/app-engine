"""Access gate and spend guard both have to actually bite."""

from __future__ import annotations

import json

import pytest

from engine import auth, limits, llm


# ---------------------------------------------------------------- password
def test_no_password_configured_means_open(monkeypatch):
    monkeypatch.delenv("APP_ENGINE_PASSWORD", raising=False)
    assert auth.configured() is False
    assert auth.check("anything") is True


def test_password_is_checked_exactly(monkeypatch):
    monkeypatch.setenv("APP_ENGINE_PASSWORD", "correct horse")
    assert auth.configured() is True
    assert auth.check("correct horse") is True
    assert auth.check("  correct horse  ") is True
    assert auth.check("wrong") is False
    assert auth.check("") is False


# ---------------------------------------------------------------- budget
@pytest.fixture()
def budget(tmp_path, monkeypatch):
    monkeypatch.setattr(limits, "STATE", tmp_path / "budget.json")
    monkeypatch.setattr(limits, "HOURLY", 2)
    monkeypatch.setattr(limits, "DAILY", 5)
    return tmp_path


def test_budget_starts_empty(budget):
    assert limits.usage()["last_hour"] == 0
    assert limits.allowed()[0] is True


def test_budget_blocks_after_the_hourly_limit(budget):
    limits.record()
    limits.record()
    ok, reason = limits.allowed()
    assert ok is False
    assert "hourly" in reason
    assert limits.usage()["last_hour"] == 2


def test_budget_persists_across_calls(budget):
    limits.record()
    state = json.loads((budget / "budget.json").read_text())
    assert len(state) == 1


def test_interpret_respects_the_budget(budget, monkeypatch):
    calls = {"n": 0}

    def fake_run(prompt, timeout=0):
        calls["n"] += 1
        return "{}"

    monkeypatch.setattr(llm, "_run", fake_run)
    limits.record()
    limits.record()

    assert llm.interpret("another idea") is None
    assert calls["n"] == 0  # blocked before spending anything


def test_interpret_records_a_call(budget, monkeypatch):
    monkeypatch.setattr(
        llm,
        "_run",
        lambda prompt, timeout=0: json.dumps(
            {
                "name": "Thing",
                "kind": "records",
                "entity": "Thing",
                "description": "x",
                "fields": [{"name": "name", "label": "Name", "type": "text", "required": True}],
            }
        ),
    )
    spec = llm.interpret("a thing tracker")
    assert spec is not None
    assert limits.usage()["last_hour"] == 1

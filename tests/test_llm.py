"""The model path must be optional, validated, and silent when it fails."""

from __future__ import annotations

import json

import pytest

from engine import llm

import pytest


@pytest.fixture(autouse=True)
def _fresh_cache():
    llm.clear_cache()
    yield
    llm.clear_cache()


GOOD = {
    "name": "Beehive inspections",
    "kind": "records",
    "entity": "Hive",
    "description": "Track hive inspections and queen status.",
    "fields": [
        {"name": "hive_id", "label": "Hive", "type": "text", "required": True},
        {"name": "temperament", "label": "Temperament", "type": "select", "options": ["Calm", "Nervous", "Aggressive"]},
        {"name": "queen_seen", "label": "Queen seen", "type": "bool"},
        {"name": "inspected", "label": "Inspected", "type": "date"},
        {"name": "notes", "label": "Notes", "type": "long_text"},
    ],
}


def test_render_json_from_fence(monkeypatch):
    monkeypatch.setattr(llm, "_run", lambda prompt, timeout=0: "```json\n" + json.dumps(GOOD) + "\n```")
    spec = llm.interpret("beehive inspections")

    assert spec is not None
    assert spec.name == "Beehive inspections"
    assert spec.entity == "Hive"
    assert [f.name for f in spec.fields] == ["hive_id", "temperament", "queen_seen", "inspected", "notes"]
    assert spec.fields[1].options == ["Calm", "Nervous", "Aggressive"]


def test_field_types_are_whitelisted(monkeypatch):
    payload = json.loads(json.dumps(GOOD))
    payload["fields"][2]["type"] = "javascript"
    monkeypatch.setattr(llm, "_run", lambda prompt, timeout=0: json.dumps(payload))
    spec = llm.interpret("beehive inspections")
    assert spec is not None
    assert spec.fields[2].type == "text"


def test_select_without_options_degrades_to_text(monkeypatch):
    payload = json.loads(json.dumps(GOOD))
    payload["fields"][1]["options"] = []
    monkeypatch.setattr(llm, "_run", lambda prompt, timeout=0: json.dumps(payload))
    spec = llm.interpret("beehive inspections")
    assert spec.fields[1].type == "text"


def test_too_many_fields_are_truncated(monkeypatch):
    payload = json.loads(json.dumps(GOOD))
    payload["fields"] = [{"name": f"f{i}", "label": f"F{i}", "type": "text"} for i in range(25)]
    monkeypatch.setattr(llm, "_run", lambda prompt, timeout=0: json.dumps(payload))
    spec = llm.interpret("a tracker")
    assert len(spec.fields) <= llm.MAX_FIELDS


def test_unknown_calculator_is_rejected(monkeypatch):
    payload = {"name": "Weird", "kind": "calculator", "calculator": "quantum", "fields": []}
    monkeypatch.setattr(llm, "_run", lambda prompt, timeout=0: json.dumps(payload))
    assert llm.interpret("something odd") is None


def test_known_calculator_is_accepted(monkeypatch):
    payload = {"name": "Loan", "kind": "calculator", "calculator": "loan", "description": "x", "fields": []}
    monkeypatch.setattr(llm, "_run", lambda prompt, timeout=0: json.dumps(payload))
    spec = llm.interpret("loan calculator")
    assert spec is not None and spec.kind == "calculator"
    assert [f.name for f in spec.fields] == ["principal", "rate", "years"]


def test_garbage_output_falls_back(monkeypatch):
    monkeypatch.setattr(llm, "_run", lambda prompt, timeout=0: "I'm sorry, I can't help with that.")
    assert llm.interpret("anything") is None


def test_timeout_and_missing_binary_fall_back(monkeypatch):
    def boom(prompt, timeout=0):
        raise RuntimeError("opencode exited 1")

    monkeypatch.setattr(llm, "_run", boom)
    assert llm.interpret("anything") is None

    monkeypatch.setattr(llm, "available", lambda: False)
    assert llm.interpret("anything") is None


def test_missing_name_field_is_added(monkeypatch):
    payload = json.loads(json.dumps(GOOD))
    payload["fields"] = [{"name": "inspected", "label": "Inspected", "type": "date"}]
    monkeypatch.setattr(llm, "_run", lambda prompt, timeout=0: json.dumps(payload))
    spec = llm.interpret("beehive inspections")
    assert spec.fields[0].name == "name"
    assert spec.fields[0].required


def test_cache_avoids_second_call(monkeypatch):
    calls = {"n": 0}

    def counting(prompt, timeout=0):
        calls["n"] += 1
        return json.dumps(GOOD)

    monkeypatch.setattr(llm, "_run", counting)
    llm.clear_cache()
    llm.interpret("beehive inspections once")
    llm.interpret("beehive inspections once")
    assert calls["n"] == 1

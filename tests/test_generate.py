"""Rendering: the generated file must be valid Python and carry the spec."""

from __future__ import annotations

import json

import pytest

from engine import generate
from engine.spec import parse_idea


def test_records_app_renders_to_valid_python(tmp_path, monkeypatch):
    monkeypatch.setattr(generate, "APPS_DIR", tmp_path)
    spec = parse_idea("A habit tracker with categories and streaks")
    source = generate.render(spec)

    compile(source, "<generated>", "exec")  # raises SyntaxError if the template drifts
    assert "SPEC = json.loads" in source
    assert "streamlit" in source
    assert "sqlite3" in source


def test_calculator_app_renders_to_valid_python():
    spec = parse_idea("Loan repayment calculator")
    source = generate.render(spec)
    compile(source, "<generated>", "exec")
    assert "monthly_payment" in source
    assert "history" in source.lower()


def test_build_writes_app_readme_and_spec(tmp_path, monkeypatch):
    monkeypatch.setattr(generate, "APPS_DIR", tmp_path)
    spec = parse_idea("Inventory list with quantity and unit cost")
    folder = generate.build(spec)

    assert (folder / "app.py").exists()
    assert (folder / "README.md").exists()
    assert (folder / "spec.json").exists()

    spec_json = json.loads((folder / "spec.json").read_text())
    assert spec_json["kind"] == "records"
    assert spec_json["entity"] == "Item"
    assert {f["name"] for f in spec_json["fields"]} >= {"name", "quantity"}


def test_slugs_stay_unique(tmp_path, monkeypatch):
    monkeypatch.setattr(generate, "APPS_DIR", tmp_path)
    first = generate.build(parse_idea("Reading list with ratings"))
    second = generate.build(parse_idea("Reading list with ratings"))
    assert first != second
    assert second.name.endswith("-2")


def test_unknown_kind_is_rejected():
    spec = parse_idea("habit tracker")
    spec.kind = "spreadsheet"
    with pytest.raises(ValueError):
        generate.render(spec)

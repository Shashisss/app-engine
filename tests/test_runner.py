"""The runner must actually boot a generated app and report it healthy."""

from __future__ import annotations

import json
import urllib.request

import pytest

from engine import generate, runner
from engine.spec import parse_idea


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    (tmp_path / "apps" / "_logs").mkdir(parents=True)
    monkeypatch.setattr(generate, "APPS_DIR", tmp_path / "apps")
    monkeypatch.setattr(runner, "APPS_DIR", tmp_path / "apps")
    monkeypatch.setattr(runner, "REGISTRY", tmp_path / "apps" / "registry.json")
    monkeypatch.setattr(runner, "LOG_DIR", tmp_path / "apps" / "_logs")
    yield tmp_path


def test_build_and_boot(sandbox):
    spec = parse_idea("A habit tracker with categories and streaks")
    folder = generate.build(spec)
    entry = runner.start(folder.name, wait=True)

    assert entry["status"] == "running", runner.tail_logs(folder.name)
    assert entry["port"] >= 8700

    with urllib.request.urlopen(f"http://127.0.0.1:{entry['port']}/_stcore/health", timeout=5) as resp:
        assert resp.status == 200

    assert runner.status(folder.name) == "running"
    assert runner.url(folder.name).endswith(str(entry["port"]))

    registry = json.loads((sandbox / "apps" / "registry.json").read_text())
    assert registry[0]["slug"] == folder.name

    runner.stop(folder.name)
    assert runner.status(folder.name) == "stopped"


def test_delete_removes_files(sandbox):
    spec = parse_idea("BMI calculator")
    folder = generate.build(spec)
    runner.start(folder.name, wait=False)
    runner.delete(folder.name)
    assert not folder.exists()
    assert runner.status(folder.name) == "missing"

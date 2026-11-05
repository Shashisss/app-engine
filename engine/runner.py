"""Start, stop and track the generated apps.

Each app is a plain Streamlit process on its own port. The registry is a JSON
file so state survives a restart of the engine itself.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = ROOT / "apps"
REGISTRY = ROOT / "apps" / "registry.json"
LOG_DIR = ROOT / "apps" / "_logs"
FIRST_PORT = 8700


# ---------------------------------------------------------------- registry
def _load() -> list[dict[str, Any]]:
    if not REGISTRY.exists():
        return []
    try:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save(rows: list[dict[str, Any]]) -> None:
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def _entry(rows: list[dict[str, Any]], slug: str) -> dict[str, Any] | None:
    return next((r for r in rows if r["slug"] == slug), None)


# ---------------------------------------------------------------- helpers
def _free_port(start: int = FIRST_PORT) -> int:
    used = {r.get("port") for r in _load()}
    port = start
    while port < start + 200:
        if port in used:
            port += 1
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                port += 1
    raise RuntimeError("no free port in range")


def _alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=2) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def wait_ready(port: int, timeout: float = 25.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _healthy(port):
            return True
        time.sleep(0.6)
    return False


def log_path(slug: str) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / f"{slug}.log"


def tail_logs(slug: str, lines: int = 40) -> str:
    path = log_path(slug)
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:])


# ---------------------------------------------------------------- lifecycle
def start(slug: str, wait: bool = True) -> dict[str, Any]:
    rows = _load()
    entry = _entry(rows, slug) or {"slug": slug}
    path = APPS_DIR / slug / "app.py"
    if not path.exists():
        raise FileNotFoundError(f"no app at {path}")

    if _alive(entry.get("pid")) and _healthy(entry.get("port", 0)):
        entry["status"] = "running"
        _save([entry if r["slug"] == slug else r for r in rows] if rows else [entry])
        return entry

    port = entry.get("port") or _free_port()
    log = log_path(slug)
    with log.open("w", encoding="utf-8") as handle:
        proc = subprocess.Popen(
            [
                sys.executable, "-m", "streamlit", "run", "app.py",
                "--server.port", str(port),
                "--server.address", "0.0.0.0",
                "--server.headless", "true",
                "--browser.gatherUsageStats", "false",
            ],
            cwd=str(APPS_DIR / slug),
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    entry.update(
        {
            "slug": slug,
            "port": port,
            "pid": proc.pid,
            "path": str(APPS_DIR / slug),
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "status": "starting",
        }
    )
    rows = [r for r in rows if r["slug"] != slug] + [entry]
    _save(rows)

    if wait and wait_ready(port):
        entry["status"] = "running"
        rows = [r for r in rows if r["slug"] != slug] + [entry]
        _save(rows)
    elif wait:
        entry["status"] = "failed to start"
        rows = [r for r in rows if r["slug"] != slug] + [entry]
        _save(rows)
    return entry


def stop(slug: str) -> None:
    rows = _load()
    entry = _entry(rows, slug)
    if not entry:
        return
    pid = entry.get("pid")
    if _alive(pid):
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
    entry["status"] = "stopped"
    entry["pid"] = None
    _save([e if e["slug"] != slug else entry for e in rows])


def delete(slug: str) -> None:
    stop(slug)
    rows = [r for r in _load() if r["slug"] != slug]
    _save(rows)
    target = APPS_DIR / slug
    if target.exists():
        for item in sorted(target.rglob("*"), reverse=True):
            item.unlink() if item.is_file() else item.rmdir()
        target.rmdir()


def status(slug: str) -> str:
    entry = _entry(_load(), slug)
    if not entry:
        return "missing"
    if _alive(entry.get("pid")) and _healthy(entry.get("port", 0)):
        return "running"
    if _alive(entry.get("pid")):
        return "starting"
    return entry.get("status", "stopped")


def url(slug: str) -> str:
    entry = _entry(_load(), slug)
    return f"http://localhost:{entry['port']}" if entry and entry.get("port") else ""


def list_apps() -> list[dict[str, Any]]:
    rows = _load()
    for row in rows:
        row["status"] = status(row["slug"])
        row["url"] = url(row["slug"])
    return sorted(rows, key=lambda r: r.get("started_at") or "", reverse=True)


def stop_all() -> None:
    for row in _load():
        stop(row["slug"])

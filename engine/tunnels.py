"""Public URLs for container-hosted apps, via cloudflared quick tunnels.

`localhost` inside the container is not reachable from the person's browser, so
every app that needs to be opened gets its own tunnel and a public URL. Tunnels
are started lazily, one per port, and reused while the process lives.

Off by default. Set APP_ENGINE_TUNNEL=1 only when you deliberately want a public link.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin" / "cloudflared"
LOG_DIR = ROOT / "apps" / "_logs"
STATE = ROOT / "apps" / "tunnels.json"
URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def enabled() -> bool:
    """Opt-in only: nothing leaves the machine unless APP_ENGINE_TUNNEL=1."""
    if os.getenv("APP_ENGINE_TUNNEL", "").lower() not in {"1", "on", "true", "yes"}:
        return False
    return binary() is not None


def binary() -> str | None:
    if BIN.exists():
        return str(BIN)
    return shutil.which("cloudflared")


def _load() -> dict[str, Any]:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save(state: dict[str, Any]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2))


def _alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _log_path(port: int) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / f"tunnel-{port}.log"


def url_for(port: int) -> str | None:
    """Existing live tunnel for this port, if any."""
    entry = _load().get(str(port))
    if entry and _alive(entry.get("pid")):
        return entry.get("url")
    return None


def start(port: int, timeout: float = 30.0) -> str | None:
    """Return a public URL for the local port, creating a tunnel if needed."""
    if not enabled():
        return None
    existing = url_for(port)
    if existing:
        return existing

    exe = binary()
    if not exe:
        return None

    log = _log_path(port)
    handle = log.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [exe, "tunnel", "--url", f"http://localhost:{port}", "--no-autoupdate"],
        stdout=handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    deadline = time.time() + timeout
    url = None
    while time.time() < deadline:
        time.sleep(1.0)
        text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        found = URL_RE.search(text)
        if found:
            url = found.group(0)
            break
        if proc.poll() is not None:
            break

    if not url:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except OSError:
            pass
        return None

    state = _load()
    state[str(port)] = {"url": url, "pid": proc.pid, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    _save(state)
    return url


def stop(port: int) -> None:
    state = _load()
    entry = state.pop(str(port), None)
    if entry and _alive(entry.get("pid")):
        try:
            os.killpg(os.getpgid(entry["pid"]), signal.SIGTERM)
        except OSError:
            pass
    _save(state)


def stop_all() -> None:
    for port in list(_load()):
        stop(int(port))


def status() -> dict[str, Any]:
    state = _load()
    return {
        "enabled": enabled(),
        "binary": binary(),
        "tunnels": {
            port: {"url": data.get("url"), "alive": _alive(data.get("pid"))}
            for port, data in state.items()
        },
    }

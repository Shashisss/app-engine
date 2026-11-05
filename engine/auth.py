"""A single shared password in front of the engine.

The engine is reachable through a public tunnel and every idea can spend the
machine's model quota, so access is gated when APP_ENGINE_PASSWORD is set.
Unset it for local-only use — the check simply disappears.
"""

from __future__ import annotations

import hmac
import os


def configured() -> bool:
    return bool(os.getenv("APP_ENGINE_PASSWORD", "").strip())


def check(candidate: str) -> bool:
    expected = os.getenv("APP_ENGINE_PASSWORD", "")
    if not expected:
        return True
    return hmac.compare_digest(candidate.strip(), expected.strip())

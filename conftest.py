import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# tests must not open public tunnels
os.environ.setdefault("APP_ENGINE_TUNNEL", "0")

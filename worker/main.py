#!/usr/bin/env python3
"""Phase 1 worker heartbeat. Publishing jobs arrive in Phase 3."""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402


def main() -> None:
    settings = get_settings()
    print(f"[fingers-worker] started env={settings.environment}", flush=True)
    while True:
        print("[fingers-worker] heartbeat ok", flush=True)
        time.sleep(60)


if __name__ == "__main__":
    main()

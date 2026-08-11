#!/usr/bin/env python3
"""Fingers worker: due posts + engagement inbox sync."""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.engagement import sync_simulated_inbox  # noqa: E402
from app.social.publisher import publish_due_posts  # noqa: E402


def main() -> None:
    settings = get_settings()
    print(f"[fingers-worker] started env={settings.environment} version={settings.app_version}", flush=True)
    cycles = 0
    while True:
        db = SessionLocal()
        try:
            count = publish_due_posts(db, limit=25)
            if count:
                print(f"[fingers-worker] published/processed {count} due post(s)", flush=True)
            # Sync simulation inbox roughly every ~2 minutes
            cycles += 1
            if cycles % 6 == 1:
                created = sync_simulated_inbox(db)
                if created:
                    print(f"[fingers-worker] synced {created} inbox interaction(s)", flush=True)
            if not count:
                print("[fingers-worker] heartbeat ok", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[fingers-worker] error: {exc}", flush=True)
            db.rollback()
        finally:
            db.close()
        time.sleep(20)


if __name__ == "__main__":
    main()

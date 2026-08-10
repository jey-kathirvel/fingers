"""celery_app = Celery('fingers', broker=REDIS_URL, include=['worker.tasks'])"""

import os

from celery import Celery

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("fingers", broker=redis_url, backend=redis_url)
celery_app.conf.update(
    task_track_started=True,
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "heartbeat-every-5-minutes": {
            "task": "worker.tasks.heartbeat",
            "schedule": 300.0,
        }
    },
)

celery_app.autodiscover_tasks(["worker"])

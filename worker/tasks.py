from datetime import datetime, timezone

from worker.celery_app import celery_app


@celery_app.task(name="worker.tasks.heartbeat")
def heartbeat() -> dict:
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}


@celery_app.task(name="worker.tasks.echo")
def echo(message: str) -> dict:
    return {"message": message, "ts": datetime.now(timezone.utc).isoformat()}

from celery import Celery
from celery.schedules import crontab

from config.settings import settings

app = Celery(
    "scrapperboi",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["workers.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3000,  # 50 min soft limit
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (memory leak prevention)
    worker_prefetch_multiplier=1,  # Fair scheduling
)

# Scheduled tasks -- stagger to avoid resource contention
app.conf.beat_schedule = {
    "scrape-rbi-daily": {
        "task": "workers.tasks.run_scraper",
        "schedule": crontab(hour=6, minute=0),  # 6:00 AM IST
        "args": ("rbi",),
    },
    # SEBI enabled after Phase 2
    # "scrape-sebi-daily": {
    #     "task": "workers.tasks.run_scraper",
    #     "schedule": crontab(hour=6, minute=30),  # 6:30 AM IST
    #     "args": ("sebi",),
    # },
}

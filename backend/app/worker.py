import os
from celery import Celery

celery_app = Celery("arth", broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"))

@celery_app.task
def ping():
    return "pong"

import os
from celery import Celery

url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("arth", broker=url, backend=url)
celery_app.conf.update(task_serializer="json", result_serializer="json",
                       accept_content=["json"], result_expires=300,
                       broker_connection_retry_on_startup=True)

@celery_app.task
def ping():
    return "pong"

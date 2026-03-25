from celery import Celery

from fetchnews.settings import Settings

settings = Settings()
celery_app = Celery("fetchnews", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.beat_schedule = {}


@celery_app.task(name="fetchnews.healthcheck")
def healthcheck() -> str:
    return "ok"

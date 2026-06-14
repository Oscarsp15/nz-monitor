"""Recolector: proceso ÚNICO con APScheduler. Arrancar con `python -m collector`.

⚠️ NO ejecutar dentro de cada worker de la API (serían N recolectores = N golpes a Netezza).
docker-compose lo arranca como servicio aparte con APP_ROLE=collector y replicas: 1.
"""
import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from config import get_settings
from store import init_db

from . import jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s [collector] %(levelname)s %(message)s")
log = logging.getLogger("collector")


def main() -> None:
    s = get_settings()
    if s.app_role != "collector":
        log.warning("APP_ROLE=%r (esperado 'collector'); arranco el recolector igual.", s.app_role)

    init_db()

    plan = [
        (jobs.HEALTH, jobs.collect_health, s.collector_health_interval_seconds),
        (jobs.SPACE_OVERVIEW, jobs.collect_space_overview, s.collector_space_interval_seconds),
    ]

    scheduler = BlockingScheduler(timezone="UTC")
    for metric_type, fn, interval in plan:
        # una pasada inmediata al arrancar + luego cada `interval` segundos
        result = jobs.run_job(metric_type, fn)
        log.info("primer recolecta %s -> %s", metric_type, result["status"])
        scheduler.add_job(
            jobs.run_job, "interval", args=[metric_type, fn], seconds=interval,
            id=metric_type, max_instances=1, coalesce=True,
        )

    log.info("recolector arrancado (health=%ss, space=%ss)",
             s.collector_health_interval_seconds, s.collector_space_interval_seconds)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("recolector detenido")


if __name__ == "__main__":
    main()

"""Background metrics and alert scheduler service."""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

scheduler = BackgroundScheduler()


def track_historical_metrics():
    """Take periodic metrics snapshot for active database instances."""
    logging.info("APScheduler: Ejecutando snapshot periódico de métricas...")


def start_scheduler():
    """Start background scheduler if not already running."""
    if not scheduler.running:
        scheduler.add_job(
            track_historical_metrics,
            trigger=IntervalTrigger(minutes=10),
            id="historical_metrics_job",
            replace_existing=True
        )
        scheduler.start()
        logging.info("APScheduler background jobs iniciados.")


def shutdown_scheduler():
    """Gracefully shutdown scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logging.info("APScheduler detenido.")

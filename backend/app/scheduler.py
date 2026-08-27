"""Background scheduling for alerts (Phase 7.8)."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.database import SessionLocal
from app.services import alert_service as alerts

logger = logging.getLogger("eduguard.scheduler")
_scheduler: BackgroundScheduler | None = None


def weekly_alert_sweep() -> None:
    """Queues this week's automatic alerts across every active unit."""
    db = SessionLocal()
    try:
        summary = alerts.sweep_all_units(db)
        if summary.get("locked_out"):
            logger.info("alert sweep skipped - another worker holds the lock")
            return
        logger.info("alert sweep: %s units, %s queued, skipped=%s", summary["units"], summary["queued"], summary["skipped"])
    except Exception:
        logger.exception("alert sweep failed")
    finally:
        db.close()


def drain_outbox_job() -> None:
    """Dispatches queued mail."""
    db = SessionLocal()
    try:
        counts = alerts.drain_outbox(db)
        if any(counts.values()):
            logger.info("outbox drained: %s", counts)
    except Exception:
        logger.exception("outbox drain failed")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler | None:
    """Seeds system templates and starts both scheduled jobs."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    db = SessionLocal()
    try:
        created = alerts.ensure_system_templates(db)
        if created:
            logger.info("seeded %s system email templates", created)
    except Exception:
        logger.exception("could not seed system email templates")
    finally:
        db.close()

    scheduler = BackgroundScheduler(timezone=settings.SCHEDULER_TIMEZONE)
    scheduler.add_job(weekly_alert_sweep, CronTrigger(day_of_week="mon", hour=8, minute=0), id="weekly_alert_sweep", replace_existing=True, coalesce=True, misfire_grace_time=3600, max_instances=1)
    scheduler.add_job(drain_outbox_job, CronTrigger(minute="*"), id="drain_outbox", replace_existing=True, coalesce=True, max_instances=1)
    scheduler.start()
    _scheduler = scheduler
    logger.info("scheduler started (%s): weekly sweep Mon 08:00, outbox drain every minute", settings.SCHEDULER_TIMEZONE)
    return scheduler


def shutdown_scheduler() -> None:
    """Stops the scheduler without waiting for a running job."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None

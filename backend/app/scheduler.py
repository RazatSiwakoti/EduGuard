"""Background scheduling for alerts (Phase 7.8)."""

import logging
import re

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


# DAY NAMES, NOT A NUMBER, AND THE REASON IS A REAL BUG.
#
# APScheduler's from_crontab() numbers day-of-week 0 = MONDAY. POSIX cron
# - and every crontab guide anyone will look up - numbers it 0 = SUNDAY.
# The strings are identical and the meanings are one day apart, so
# "0 8 * * 1" reads as Monday and fires on TUESDAY. Verified against
# APScheduler directly rather than assumed: with a Friday reference date,
# "0 8 * * 1" resolves to Tuesday 1 September and "0 8 * * mon" to Monday
# 31 August.
#
# A weekly job that runs on the wrong day still runs, still logs success,
# and still queues real email. Nothing ever reports it as broken - the
# lecturer summary simply arrives on the wrong morning, forever. So
# numbers in that field are TRANSLATED from what the operator meant to
# what APScheduler expects, and the default is written as a name.
DEFAULT_SWEEP_CRON = "0 8 * * mon"

# POSIX day-of-week numbering, which is what someone editing a .env will
# have in mind.
_POSIX_DAYS = {"0": "sun", "1": "mon", "2": "tue", "3": "wed", "4": "thu", "5": "fri", "6": "sat", "7": "sun"}
_PLAIN_NUMERIC = re.compile(r"^[0-7](?:[,-][0-7])*$")


def normalise_day_of_week(expression: str) -> str:
    """
    Rewrites a numeric day-of-week field into day names.

    Only touches a field made entirely of digits, commas and hyphens, so
    "1" becomes "mon" and "1-5" becomes "mon-fri", while "*" and any
    step syntax like "*/2" are passed through untouched - a digit inside
    a step is a step size, not a day, and rewriting it would be its own
    silent bug.
    """
    fields = (expression or "").split()
    if len(fields) != 5 or not _PLAIN_NUMERIC.match(fields[4]):
        return expression
    fields[4] = re.sub(r"[0-7]", lambda m: _POSIX_DAYS[m.group(0)], fields[4])
    return " ".join(fields)


def sweep_trigger() -> CronTrigger:
    """
    Builds the sweep's trigger from ALERT_SWEEP_CRON.

    FALLS BACK RATHER THAN RAISES. A typo in a cron string is a config
    error, and the tempting response is to refuse to start. But this
    trigger is built inside the FastAPI startup hook, so raising here
    takes down the whole API - login, dashboards, reports - because one
    optional scheduling line has a stray character. Logging loudly and
    running on the known-good default keeps the failure proportional to
    the mistake.
    """
    raw = (settings.ALERT_SWEEP_CRON or "").strip() or DEFAULT_SWEEP_CRON
    expression = normalise_day_of_week(raw)
    if expression != raw:
        logger.info("ALERT_SWEEP_CRON %r read as %r (day-of-week translated to APScheduler's numbering)", raw, expression)
    try:
        return CronTrigger.from_crontab(expression)
    except ValueError:
        logger.error("ALERT_SWEEP_CRON is not a valid 5-field cron expression (%r) - falling back to %r", raw, DEFAULT_SWEEP_CRON)
        return CronTrigger.from_crontab(DEFAULT_SWEEP_CRON)


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
    scheduler.add_job(weekly_alert_sweep, sweep_trigger(), id="weekly_alert_sweep", replace_existing=True, coalesce=True, misfire_grace_time=3600, max_instances=1)
    scheduler.add_job(drain_outbox_job, CronTrigger(minute="*"), id="drain_outbox", replace_existing=True, coalesce=True, max_instances=1)
    scheduler.start()
    _scheduler = scheduler
    logger.info("scheduler started (%s): sweep '%s', outbox drain every minute", settings.SCHEDULER_TIMEZONE, settings.ALERT_SWEEP_CRON)
    return scheduler


def shutdown_scheduler() -> None:
    """Stops the scheduler without waiting for a running job."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None

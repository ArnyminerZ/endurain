"""Scheduled work owned by live tracking."""

import core.database as core_database
import core.scheduler as core_scheduler
import modules.live_tracking.service as live_tracking_service

_FINISH_LOCK_NAME = "live_tracking_finish_stale"


def finish_stale_sessions() -> None:
    """End sessions that expired or went quiet and purge old ended ones.

    Scheduler-invoked, with no request to carry a session, so it opens its own.
    """
    with core_database.SessionLocal() as db:
        live_tracking_service.finish_stale_sessions(db)


def recurring_jobs() -> tuple[core_scheduler.ScheduledJob, ...]:
    """Return the live tracking jobs.

    Returns:
        The jobs to schedule.
    """
    return (
        core_scheduler.ScheduledJob(
            finish_stale_sessions,
            5,
            "end expired or silent live tracking sessions",
            lock_name=_FINISH_LOCK_NAME,
        ),
    )

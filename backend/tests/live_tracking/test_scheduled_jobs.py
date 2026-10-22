from unittest.mock import MagicMock, patch

import modules.live_tracking.scheduled_jobs as scheduled_jobs


def test_recurring_job_is_locked_and_periodic():
    (job,) = scheduled_jobs.recurring_jobs()
    assert job.func is scheduled_jobs.finish_stale_sessions
    assert job.lock_name
    assert job.minutes <= 10


def test_job_opens_its_own_session():
    session = MagicMock()
    with (
        patch.object(scheduled_jobs.core_database, "SessionLocal") as factory,
        patch.object(scheduled_jobs.live_tracking_service, "finish_stale_sessions") as finish,
    ):
        factory.return_value.__enter__.return_value = session
        scheduled_jobs.finish_stale_sessions()
    finish.assert_called_once_with(session)

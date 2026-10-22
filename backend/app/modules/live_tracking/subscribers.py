"""Event subscribers for the live tracking module."""

import jasil.event_versioning as platform_event_versioning
import jasil.runtime as platform_runtime
from jasil.events import Event
from jasil.jobs.registry import JobHandlerRegistry
from jasil.providers import EventBusProvider
from jasil.subscribers import best_effort

import core.database as core_database
import core.logger as core_logger
import modules.live_tracking.events as live_tracking_events
import modules.live_tracking.service as live_tracking_service

logger = core_logger.get_logger(__name__)

LIVE_SESSION_EMAIL_SUBSCRIBER_ID = "live_tracking.send_session_started_emails"


def send_session_started_emails_for_event(event: Event) -> None:
    """Email the contacts for a ``live_tracking.session_started`` event.

    Raises:
        MailError: On a transient delivery failure, so the durable job is retried.
    """
    payload = platform_event_versioning.parse_payload(live_tracking_events.LiveSessionStartedPayload, event)
    mail = platform_runtime.get_active_platform().mail
    with core_database.SessionLocal() as db:
        sent = live_tracking_service.send_session_started_emails(payload.session_id, payload.contact_ids, mail, db)
    logger.debug("Live session emails sent", extra=core_logger.context(session_id=payload.session_id, sent=sent))


on_live_session_started = best_effort(send_session_started_emails_for_event)


def register_bus_subscribers(events: EventBusProvider) -> None:
    """Register the live tracking event consumers on the running bus."""
    events.subscribe(live_tracking_events.LIVE_SESSION_STARTED, on_live_session_started)


def register_durable_handlers(registry: JobHandlerRegistry) -> None:
    """Register the retryable live tracking event consumers."""
    registry.register(
        live_tracking_events.LIVE_SESSION_STARTED,
        LIVE_SESSION_EMAIL_SUBSCRIBER_ID,
        send_session_started_emails_for_event,
    )

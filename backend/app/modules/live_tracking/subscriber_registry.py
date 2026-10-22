"""Registration surface and reconciliation declarations for live tracking."""

from jasil.jobs.reconciliation import DurableSubscriberNet
from jasil.jobs.registry import JobHandlerRegistry
from jasil.providers import EventBusProvider

import modules.live_tracking.subscribers as live_tracking_subscribers


def register_bus_subscribers(events: EventBusProvider) -> None:
    """Register the live tracking bus subscribers."""
    live_tracking_subscribers.register_bus_subscribers(events)


def register_durable_handlers(registry: JobHandlerRegistry) -> None:
    """Register the live tracking durable handlers."""
    live_tracking_subscribers.register_durable_handlers(registry)


DURABLE_SUBSCRIBER_NETS: tuple[DurableSubscriberNet, ...] = (
    DurableSubscriberNet(
        live_tracking_subscribers.LIVE_SESSION_EMAIL_SUBSCRIBER_ID,
        None,
        exempt_reason=(
            "A start notification is only useful while the session is live; a lost one is not worth "
            "replaying later, and the owner can always copy the link from the app."
        ),
    ),
)

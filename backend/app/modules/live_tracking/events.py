"""Domain event channels owned by the live tracking module.

Payloads carry ids only: events can be persisted, and the share link is derived
by the subscriber from the session id rather than travelling in the event.
"""

from typing import ClassVar

from jasil.event_versioning import VersionedPayload
from pydantic import ConfigDict

# Published after a live session started, so the user's contacts can be emailed.
LIVE_SESSION_STARTED = "live_tracking.session_started"


class LiveSessionStartedPayload(VersionedPayload):
    """Validated payload for the ``live_tracking.session_started`` event.

    Attributes:
        session_id: The session that started.
        contact_ids: The contacts to notify.
    """

    model_config = ConfigDict(extra="ignore")

    SCHEMA_VERSION: ClassVar[int] = 1

    session_id: str
    contact_ids: list[int]

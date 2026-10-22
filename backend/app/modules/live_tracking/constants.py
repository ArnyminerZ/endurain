"""Domain constants for live tracking sessions."""

from datetime import timedelta
from enum import StrEnum


class SessionStatus(StrEnum):
    """Lifecycle status of a live session.

    Attributes:
        ACTIVE: The session is live and its share link works.
        ENDED: The session was stopped, cancelled or expired; the link is dead.
    """

    ACTIVE = "active"
    ENDED = "ended"


#: Most points accepted by one push request.
MAX_POINTS_PER_PUSH = 200

#: Most points kept for one session; later pushes are rejected.
MAX_POINTS_PER_SESSION = 100_000

#: How far in the future a client clock may run before a point is rejected.
MAX_POINT_FUTURE_SKEW = timedelta(minutes=5)

#: How long before the session start a buffered point is still accepted.
MAX_POINT_BEFORE_START = timedelta(minutes=5)

#: How long an ended session row is kept before the scheduler purges it.
ENDED_RETENTION = timedelta(hours=24)

#: How often (seconds) a client is assumed to push when it does not say.
DEFAULT_UPDATE_INTERVAL_SECONDS = 10

#: Bounds for the push interval a client may declare, in seconds.
MIN_UPDATE_INTERVAL_SECONDS = 1
MAX_UPDATE_INTERVAL_SECONDS = 600

#: Most points the public view returns in one response.
MAX_PUBLIC_POINTS = 5000

#: Activity type label used when the client does not name one.
DEFAULT_ACTIVITY_TYPE = "Workout"

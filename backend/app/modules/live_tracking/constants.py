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

#: Fewest points that make a worthwhile activity; fewer are discarded on stop.
MIN_POINTS_FOR_ACTIVITY = 2

#: How long an ended session whose activity could not be created keeps its points.
ENDED_RETENTION = timedelta(hours=24)

#: Most points the public view returns in one response.
MAX_PUBLIC_POINTS = 5000

#: Activity type used when the client does not name one (maps to "Workout").
DEFAULT_ACTIVITY_TYPE = "Workout"

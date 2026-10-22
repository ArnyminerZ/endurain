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


class PositionSource(StrEnum):
    """Where the position of a point was measured.

    Attributes:
        GADGET: The recording gadget's own GPS (e.g. the watch).
        PHONE: The phone's GPS, used when the gadget has no fix or none to give.
    """

    GADGET = "gadget"
    PHONE = "phone"


class SignalType(StrEnum):
    """The kind of mobile signal measurement a ``phone_signal_dbm`` value is.

    The same dBm number means different things for each: the thresholds that
    separate a good signal from a bad one differ, so viewers need to know which
    one they are looking at.

    Attributes:
        RSRP: LTE or 5G reference signal received power (the usual one on modern phones).
        RSSI: Received signal strength indicator (GSM, or the LTE total).
        RSCP: UMTS (3G) received signal code power.
    """

    RSRP = "rsrp"
    RSSI = "rssi"
    RSCP = "rscp"


#: Valid range of a mobile signal reading in dBm.
MIN_SIGNAL_DBM = -150
MAX_SIGNAL_DBM = 0

#: Largest horizontal accuracy radius accepted, in meters.
MAX_HORIZONTAL_ACCURACY_M = 100_000

#: Most satellites a single fix can report (all constellations together).
MAX_SATELLITES = 100

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

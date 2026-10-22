"""ORM↔schema transformation for live tracking.

``crud`` calls this at its edge so ORM rows never leave the persistence layer.
"""

import modules.live_tracking.models as live_tracking_models
import modules.live_tracking.schema as live_tracking_schema


def to_session_schema(session: live_tracking_models.LiveSession) -> live_tracking_schema.LiveSessionRead:
    """Convert a LiveSession row into its DTO.

    Args:
        session: The ORM row.

    Returns:
        The session DTO.
    """
    return live_tracking_schema.LiveSessionRead.model_validate(session)


def to_point_schema(point: live_tracking_models.LivePoint) -> live_tracking_schema.LivePointRead:
    """Convert a LivePoint row into its DTO.

    Args:
        point: The ORM row.

    Returns:
        The point DTO.
    """
    return live_tracking_schema.LivePointRead.model_validate(point)


def to_contact_schema(contact: live_tracking_models.LiveContact) -> live_tracking_schema.LiveContactRead:
    """Convert a LiveContact row into its DTO.

    Args:
        contact: The ORM row.

    Returns:
        The contact DTO.
    """
    return live_tracking_schema.LiveContactRead.model_validate(contact)

"""Render a live session's points as a GPX document for the ingestion pipeline."""

from collections.abc import Sequence
from xml.sax.saxutils import escape

import modules.live_tracking.schema as live_tracking_schema

_HEADER = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<gpx version="1.1" creator="Endurain Live" xmlns="http://www.topografix.com/GPX/1/1" '
    'xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1">\n'
)


def _extensions(point: live_tracking_schema.LivePointRead) -> str:
    """Return the heart-rate / cadence / temperature extension block for a point.

    Skin temperature has no GPX equivalent, so it is only shown live.

    Args:
        point: The point to render.

    Returns:
        The ``<extensions>`` element, or an empty string when the point has no sensors.
    """
    parts = []
    if point.heart_rate is not None:
        parts.append(f"<gpxtpx:hr>{point.heart_rate}</gpxtpx:hr>")
    if point.temperature is not None:
        parts.append(f"<gpxtpx:atemp>{point.temperature}</gpxtpx:atemp>")
    if point.cadence is not None:
        parts.append(f"<gpxtpx:cad>{point.cadence}</gpxtpx:cad>")
    if not parts:
        return ""
    return f"<extensions><gpxtpx:TrackPointExtension>{''.join(parts)}</gpxtpx:TrackPointExtension></extensions>"


def build_gpx(points: Sequence[live_tracking_schema.LivePointRead], name: str | None, activity_type: str) -> str:
    """Build a single-track GPX document.

    Args:
        points: The points in chronological order.
        name: Optional track name.
        activity_type: Activity type name written to the track ``<type>``.

    Returns:
        The GPX XML text.
    """
    lines = [_HEADER, "<trk>"]
    if name:
        lines.append(f"<name>{escape(name)}</name>")
    lines.append(f"<type>{escape(activity_type)}</type>")
    lines.append("<trkseg>")
    for point in points:
        elevation = f"<ele>{point.elevation}</ele>" if point.elevation is not None else ""
        lines.append(
            f'<trkpt lat="{point.latitude}" lon="{point.longitude}">{elevation}'
            f"<time>{point.recorded_at.isoformat()}</time>{_extensions(point)}</trkpt>"
        )
    lines.append("</trkseg></trk>\n</gpx>\n")
    return "\n".join(lines)

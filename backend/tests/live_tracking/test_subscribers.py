from unittest.mock import MagicMock, patch

import modules.live_tracking.event_publishers as event_publishers
import modules.live_tracking.events as live_tracking_events
import modules.live_tracking.subscribers as subscribers


def test_publisher_sends_ids_only():
    commit = MagicMock()
    with patch.object(event_publishers.platform_publisher, "publish_committing") as publish:
        event_publishers.publish_live_session_started(7, "sid", [1, 2], MagicMock(), commit=commit)
    channel, payload = publish.call_args.args
    assert channel == live_tracking_events.LIVE_SESSION_STARTED
    assert payload == {"session_id": "sid", "contact_ids": [1, 2]}
    assert publish.call_args.kwargs["commit"] is commit


def test_subscriber_sends_through_the_service():
    event = MagicMock()
    parsed = live_tracking_events.LiveSessionStartedPayload(session_id="sid", contact_ids=[1])
    with (
        patch.object(subscribers.platform_event_versioning, "parse_payload", return_value=parsed),
        patch.object(subscribers.platform_runtime, "get_active_platform") as platform,
        patch.object(subscribers.core_database, "SessionLocal") as factory,
        patch.object(subscribers.live_tracking_service, "send_session_started_emails", return_value=1) as send,
    ):
        factory.return_value.__enter__.return_value = "db"
        subscribers.send_session_started_emails_for_event(event)
    send.assert_called_once_with("sid", [1], platform.return_value.mail, "db")

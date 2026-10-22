from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import core.exceptions as core_exceptions
import modules.live_tracking.constants as live_tracking_constants
import modules.live_tracking.crud as live_tracking_crud
import modules.live_tracking.schema as live_tracking_schema
import modules.live_tracking.service as live_tracking_service
import modules.live_tracking.share_token as live_tracking_share_token
from tests.live_tracking.conftest import USER_ID, point, push, track

_USER = SimpleNamespace(id=USER_ID, name="Arnau Mora", preferred_language="en")


@pytest.fixture(autouse=True)
def _config():
    with patch.object(live_tracking_service.core_config, "read_secret", return_value="unit-secret"):
        yield


@pytest.fixture
def no_mail():
    with patch.object(live_tracking_service.core_mail, "is_mail_configured", return_value=False):
        yield


def _start(db, **kwargs):
    data = live_tracking_schema.LiveSessionStart(**kwargs)
    return live_tracking_service.start_session(USER_ID, data, db)


class TestStartSession:
    def test_returns_a_working_share_link(self, db, no_mail):
        started = _start(db, activity_type="Run", name="Morning")
        token = started.share_url.rsplit("/live/", 1)[1]
        assert live_tracking_share_token.parse_token(token, "unit-secret") == started.session.id
        assert started.session.status == live_tracking_constants.SessionStatus.ACTIVE
        assert started.notified_contacts == 0
        assert started.email_enabled is False

    def test_second_active_session_conflicts(self, db, no_mail):
        _start(db)
        with pytest.raises(core_exceptions.ConflictError):
            _start(db)

    def test_disabled_feature_refuses(self, db):
        with (
            patch.object(live_tracking_service.core_config.settings, "LIVE_TRACKING_ENABLED", False),
            pytest.raises(core_exceptions.ServiceUnavailableError),
        ):
            _start(db)

    def test_unknown_contact_is_rejected(self, db, no_mail):
        with pytest.raises(core_exceptions.InvalidInputError):
            _start(db, notify_contact_ids=[999])

    def test_publishes_email_event_for_selected_contacts(self, db):
        first = live_tracking_service.add_contact(
            USER_ID, live_tracking_schema.LiveContactCreate(name="Ana", email="ana@example.com"), db
        )
        live_tracking_service.add_contact(
            USER_ID, live_tracking_schema.LiveContactCreate(name="Bo", email="bo@example.com"), db
        )
        with (
            patch.object(live_tracking_service.core_mail, "is_mail_configured", return_value=True),
            patch.object(live_tracking_service.live_tracking_event_publishers, "publish_live_session_started") as pub,
        ):
            pub.side_effect = lambda *a, commit, **k: commit()
            started = _start(db, notify_contact_ids=[first.id])
        assert started.notified_contacts == 1
        assert pub.call_args.args[2] == [first.id]

    def test_no_contacts_still_commits(self, db):
        with patch.object(live_tracking_service.core_mail, "is_mail_configured", return_value=True):
            started = _start(db)
        assert live_tracking_crud.get_session(started.session.id, db) is not None


class TestPushPoints:
    def test_stores_and_dedupes(self, db, now, no_mail):
        started = _start(db)
        batch = push(track(now))
        first = live_tracking_service.push_points(started.session.id, USER_ID, batch, db)
        again = live_tracking_service.push_points(started.session.id, USER_ID, batch, db)
        assert (first.accepted, first.total_points) == (3, 3)
        assert (again.accepted, again.total_points) == (0, 3)

    def test_updates_last_update(self, db, now, no_mail):
        started = _start(db)
        live_tracking_service.push_points(started.session.id, USER_ID, push(track(now, 1)), db)
        session = live_tracking_crud.get_session(started.session.id, db)
        assert session.last_update_at >= started.session.last_update_at

    def test_other_user_cannot_push(self, db, now, no_mail):
        started = _start(db)
        with pytest.raises(core_exceptions.AccessConcealedError):
            live_tracking_service.push_points(started.session.id, USER_ID + 1, push(track(now)), db)

    def test_rejects_naive_future_and_ancient_points(self, db, now, no_mail):
        started = _start(db)
        for bad in (
            now.replace(tzinfo=None),
            now + timedelta(hours=1),
            now - timedelta(days=2),
        ):
            with pytest.raises(core_exceptions.InvalidInputError):
                live_tracking_service.push_points(started.session.id, USER_ID, push([point(bad)]), db)

    def test_ended_session_refuses_points(self, db, now, no_mail):
        started = _start(db)
        live_tracking_service.stop_session(started.session.id, USER_ID, db)
        with pytest.raises(core_exceptions.ConflictError):
            live_tracking_service.push_points(started.session.id, USER_ID, push(track(now)), db)

    def test_session_point_cap(self, db, now, no_mail):
        started = _start(db)
        with (
            patch.object(live_tracking_constants, "MAX_POINTS_PER_SESSION", 2),
            pytest.raises(core_exceptions.InvalidInputError),
        ):
            live_tracking_service.push_points(started.session.id, USER_ID, push(track(now, 3)), db)


class TestStopSession:
    def test_ends_session_deletes_points_and_creates_no_activity(self, db, now, no_mail):
        started = _start(db, activity_type="Run", name="Morning")
        live_tracking_service.push_points(started.session.id, USER_ID, push(track(now)), db)
        token = started.share_url.rsplit("/live/", 1)[1]
        assert not hasattr(live_tracking_service, "activity_ingestion_integration")
        stopped = live_tracking_service.stop_session(started.session.id, USER_ID, db)
        assert stopped.status == live_tracking_constants.SessionStatus.ENDED
        assert stopped.ended_at is not None
        assert live_tracking_crud.count_points(started.session.id, db) == 0
        with pytest.raises(core_exceptions.NotFoundError):
            live_tracking_service.get_public_view(token, None, db)

    def test_stopping_twice_is_harmless(self, db, no_mail):
        started = _start(db)
        first = live_tracking_service.stop_session(started.session.id, USER_ID, db)
        second = live_tracking_service.stop_session(started.session.id, USER_ID, db)
        assert second.ended_at == first.ended_at

    def test_other_user_cannot_stop(self, db, no_mail):
        started = _start(db)
        with pytest.raises(core_exceptions.AccessConcealedError):
            live_tracking_service.stop_session(started.session.id, USER_ID + 1, db)

    def test_new_session_possible_after_stop(self, db, no_mail):
        started = _start(db)
        live_tracking_service.stop_session(started.session.id, USER_ID, db)
        assert _start(db).session.id != started.session.id


class TestCancelSession:
    def test_deletes_everything(self, db, now, no_mail):
        started = _start(db)
        live_tracking_service.push_points(started.session.id, USER_ID, push(track(now)), db)
        live_tracking_service.cancel_session(started.session.id, USER_ID, db)
        assert live_tracking_crud.get_session(started.session.id, db) is None
        assert live_tracking_crud.count_points(started.session.id, db) == 0


class TestPublicView:
    def test_returns_track_without_private_fields(self, db, now, no_mail):
        started = _start(db, activity_type="Run", name="Morning")
        live_tracking_service.push_points(started.session.id, USER_ID, push(track(now)), db)
        token = started.share_url.rsplit("/live/", 1)[1]
        with patch.object(live_tracking_service.users_integration, "get_user", return_value=_USER):
            view = live_tracking_service.get_public_view(token, None, db)
        assert view.athlete == "Arnau"
        assert view.total_points == 3
        assert len(view.points) == 3
        assert view.latest.latitude == pytest.approx(39.002)
        assert "user_id" not in view.model_dump()
        assert "id" not in view.model_dump()

    def test_since_returns_only_newer_points(self, db, now, no_mail):
        started = _start(db)
        points = track(now)
        live_tracking_service.push_points(started.session.id, USER_ID, push(points), db)
        token = started.share_url.rsplit("/live/", 1)[1]
        with patch.object(live_tracking_service.users_integration, "get_user", return_value=_USER):
            view = live_tracking_service.get_public_view(token, points[0].recorded_at, db)
        assert len(view.points) == 2
        assert view.total_points == 3

    def test_bad_tokens_and_ended_sessions_are_all_not_found(self, db, no_mail):
        started = _start(db)
        token = started.share_url.rsplit("/live/", 1)[1]
        for bad in ("nope", token[:-3] + "abc", "a" * 32 + ".b"):
            with pytest.raises(core_exceptions.NotFoundError) as unknown:
                live_tracking_service.get_public_view(bad, None, db)
        live_tracking_service.stop_session(started.session.id, USER_ID, db)
        with pytest.raises(core_exceptions.NotFoundError) as ended:
            live_tracking_service.get_public_view(token, None, db)
        assert str(ended.value) == str(unknown.value)

    def test_disabled_feature_hides_links(self, db, no_mail):
        started = _start(db)
        token = started.share_url.rsplit("/live/", 1)[1]
        with (
            patch.object(live_tracking_service.core_config.settings, "LIVE_TRACKING_ENABLED", False),
            pytest.raises(core_exceptions.NotFoundError),
        ):
            live_tracking_service.get_public_view(token, None, db)


class TestStaleSessions:
    def test_silent_session_is_finished_and_link_dies(self, db, now, no_mail):
        started = _start(db)
        live_tracking_service.push_points(started.session.id, USER_ID, push(track(now)), db)
        with patch.object(live_tracking_service, "_now", return_value=now + timedelta(hours=1)):
            assert live_tracking_service.finish_stale_sessions(db) == 1
        assert live_tracking_crud.count_points(started.session.id, db) == 0
        assert (
            live_tracking_crud.get_session(started.session.id, db).status == live_tracking_constants.SessionStatus.ENDED
        )

    def test_recent_session_is_left_alone(self, db, no_mail):
        _start(db)
        assert live_tracking_service.finish_stale_sessions(db) == 0

    def test_one_failure_does_not_stop_the_sweep(self, db, now, no_mail):
        _start(db)
        with (
            patch.object(live_tracking_service, "_now", return_value=now + timedelta(days=2)),
            patch.object(live_tracking_service, "_end_session", side_effect=RuntimeError("boom")),
        ):
            assert live_tracking_service.finish_stale_sessions(db) == 0

    def test_old_ended_sessions_are_purged(self, db, now, no_mail):
        started = _start(db)
        live_tracking_service.stop_session(started.session.id, USER_ID, db)
        with patch.object(live_tracking_service, "_now", return_value=now + timedelta(days=2)):
            live_tracking_service.finish_stale_sessions(db)
        assert live_tracking_crud.get_session(started.session.id, db) is None


class TestContacts:
    def test_add_list_remove(self, db):
        created = live_tracking_service.add_contact(
            USER_ID, live_tracking_schema.LiveContactCreate(name="Ana", email="Ana@Example.com"), db
        )
        assert created.email == "ana@example.com"
        assert [c.id for c in live_tracking_service.list_contacts(USER_ID, db)] == [created.id]
        live_tracking_service.remove_contact(created.id, USER_ID, db)
        assert live_tracking_service.list_contacts(USER_ID, db) == []

    def test_duplicate_email_conflicts(self, db):
        data = live_tracking_schema.LiveContactCreate(name="Ana", email="ana@example.com")
        live_tracking_service.add_contact(USER_ID, data, db)
        with pytest.raises(core_exceptions.ConflictError):
            live_tracking_service.add_contact(USER_ID, data, db)

    def test_limit(self, db):
        with patch.object(live_tracking_service.core_config.settings, "LIVE_TRACKING_MAX_CONTACTS", 1):
            live_tracking_service.add_contact(
                USER_ID, live_tracking_schema.LiveContactCreate(name="A", email="a@example.com"), db
            )
            with pytest.raises(core_exceptions.InvalidInputError):
                live_tracking_service.add_contact(
                    USER_ID, live_tracking_schema.LiveContactCreate(name="B", email="b@example.com"), db
                )

    def test_cannot_remove_someone_elses(self, db):
        created = live_tracking_service.add_contact(
            USER_ID, live_tracking_schema.LiveContactCreate(name="Ana", email="ana@example.com"), db
        )
        with pytest.raises(core_exceptions.NotFoundError):
            live_tracking_service.remove_contact(created.id, USER_ID + 1, db)


class TestSessionStartedEmails:
    def _contact(self, db, email="ana@example.com"):
        return live_tracking_service.add_contact(
            USER_ID, live_tracking_schema.LiveContactCreate(name="Ana", email=email), db
        )

    def test_sends_to_selected_contacts_only(self, db, no_mail):
        wanted = self._contact(db)
        self._contact(db, "other@example.com")
        started = _start(db)
        with (
            patch.object(live_tracking_service.users_integration, "get_user", return_value=_USER),
            patch.object(live_tracking_service.core_mail, "send_email", return_value=True) as send,
        ):
            sent = live_tracking_service.send_session_started_emails(started.session.id, [wanted.id], MagicMock(), db)
        assert sent == 1
        assert send.call_args.args[1] == "ana@example.com"
        assert started.share_url in send.call_args.args[3]

    def test_ended_session_sends_nothing(self, db, no_mail):
        wanted = self._contact(db)
        started = _start(db)
        live_tracking_service.stop_session(started.session.id, USER_ID, db)
        with patch.object(live_tracking_service.core_mail, "send_email") as send:
            assert (
                live_tracking_service.send_session_started_emails(started.session.id, [wanted.id], MagicMock(), db) == 0
            )
        send.assert_not_called()

    def test_transient_failure_is_raised_after_trying_everyone(self, db, no_mail):
        import jasil.providers as platform_providers

        first = self._contact(db)
        second = self._contact(db, "b@example.com")
        started = _start(db)
        calls = []

        def flaky(mail, to, *args):
            calls.append(to)
            if to == "ana@example.com":
                raise platform_providers.MailError("down")
            return True

        with (
            patch.object(live_tracking_service.users_integration, "get_user", return_value=_USER),
            patch.object(live_tracking_service.core_mail, "send_email", side_effect=flaky),
            pytest.raises(platform_providers.MailError),
        ):
            live_tracking_service.send_session_started_emails(
                started.session.id, [first.id, second.id], MagicMock(), db
            )
        assert sorted(calls) == ["ana@example.com", "b@example.com"]

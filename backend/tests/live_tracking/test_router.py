from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import core.database as core_db
import core.exceptions as core_exceptions
import modules.auth.dependencies as auth_deps
import modules.live_tracking.public_router as public_router
import modules.live_tracking.router as router
import modules.live_tracking.service as live_tracking_service
from tests.live_tracking.conftest import USER_ID

_PUSH = {"points": [{"recorded_at": "2026-10-22T10:00:00+00:00", "latitude": 39.0, "longitude": -0.5}]}


@pytest.fixture(autouse=True)
def _config():
    with (
        patch.object(live_tracking_service.core_config, "read_secret", return_value="unit-secret"),
        patch.object(live_tracking_service.core_mail, "is_mail_configured", return_value=False),
        patch.object(
            live_tracking_service.users_integration,
            "get_user",
            return_value=SimpleNamespace(id=USER_ID, name="Arnau Mora", preferred_language="en"),
        ),
    ):
        yield


def _app(db, user_id=USER_ID):
    app = FastAPI()
    app.include_router(router.router, prefix="/live")
    app.include_router(public_router.router, prefix="/public/live")
    core_exceptions.register_exception_handlers(app)
    app.dependency_overrides[auth_deps.check_scopes] = lambda: None
    app.dependency_overrides[auth_deps.get_sub_from_access_token] = lambda: user_id
    app.dependency_overrides[core_db.get_db] = lambda: db
    return app


@pytest.fixture
def client(db):
    return TestClient(_app(db))


def _start(client, **body):
    response = client.post("/live/sessions", json=body)
    assert response.status_code == 201, response.text
    return response.json()


class TestLifecycle:
    def test_full_flow_with_anonymous_viewer(self, client, now):
        started = _start(client, activity_type="Run", name="Morning")
        session_id = started["session"]["id"]
        token = started["share_url"].rsplit("/live/", 1)[1]

        at = (now - timedelta(seconds=30)).isoformat()
        later = (now - timedelta(seconds=20)).isoformat()
        pushed = client.post(
            f"/live/sessions/{session_id}/points",
            json={
                "points": [
                    {"recorded_at": at, "latitude": 39.0, "longitude": -0.5, "heart_rate": 130},
                    {"recorded_at": later, "latitude": 39.001, "longitude": -0.5},
                ]
            },
        )
        assert pushed.json() == {"accepted": 2, "total_points": 2}

        # No auth override on the viewer's side: a different, anonymous app context.
        viewer = client.get(f"/public/live/{token}")
        assert viewer.status_code == 200
        assert viewer.headers["cache-control"] == "no-store"
        body = viewer.json()
        assert body["athlete"] == "Arnau"
        assert len(body["points"]) == 2
        assert "user_id" not in body

        newer = client.get(f"/public/live/{token}", params={"since": at})
        assert len(newer.json()["points"]) == 1

        stopped = client.post(f"/live/sessions/{session_id}/stop")
        assert stopped.status_code == 200
        assert stopped.json()["status"] == "ended"

        assert client.get(f"/public/live/{token}").status_code == 404

    def test_temperatures_round_trip_to_the_viewer(self, client, now):
        started = _start(client)
        token = started["share_url"].rsplit("/live/", 1)[1]
        point = {
            "recorded_at": (now - timedelta(seconds=5)).isoformat(),
            "latitude": 39.0,
            "longitude": -0.5,
            "temperature": 21.5,
            "skin_temperature": 33.4,
        }
        pushed = client.post(f"/live/sessions/{started['session']['id']}/points", json={"points": [point]})
        assert pushed.status_code == 200
        latest = client.get(f"/public/live/{token}").json()["latest"]
        assert (latest["temperature"], latest["skin_temperature"]) == (21.5, 33.4)

    def test_update_interval_is_validated_and_reaches_the_viewer(self, client):
        assert client.post("/live/sessions", json={"update_interval_seconds": 0}).status_code == 422
        assert client.post("/live/sessions", json={"update_interval_seconds": 601}).status_code == 422
        started = _start(client, update_interval_seconds=45)
        token = started["share_url"].rsplit("/live/", 1)[1]
        assert client.get(f"/public/live/{token}").json()["update_interval_seconds"] == 45

    def test_device_status_round_trips_to_the_viewer(self, client, now):
        started = _start(client)
        token = started["share_url"].rsplit("/live/", 1)[1]
        point = {
            "recorded_at": (now - timedelta(seconds=5)).isoformat(),
            "latitude": 39.0,
            "longitude": -0.5,
            "gadget_battery": 62,
            "phone_battery": 18,
            "phone_signal": 1,
        }
        assert (
            client.post(f"/live/sessions/{started['session']['id']}/points", json={"points": [point]}).status_code
            == 200
        )
        latest = client.get(f"/public/live/{token}").json()["latest"]
        assert (latest["gadget_battery"], latest["phone_battery"], latest["phone_signal"]) == (62, 18, 1)

    @pytest.mark.parametrize(
        "extra",
        [{"gadget_battery": 101}, {"phone_battery": -1}, {"phone_signal": 5}, {"phone_signal": -1}],
    )
    def test_rejects_out_of_range_device_status(self, client, now, extra):
        started = _start(client)
        point = {"recorded_at": now.isoformat(), "latitude": 1, "longitude": 1, **extra}
        response = client.post(f"/live/sessions/{started['session']['id']}/points", json={"points": [point]})
        assert response.status_code == 422

    def test_rejects_implausible_temperatures(self, client, now):
        started = _start(client)
        url = f"/live/sessions/{started['session']['id']}/points"
        base = {"recorded_at": now.isoformat(), "latitude": 1, "longitude": 1}
        assert client.post(url, json={"points": [{**base, "temperature": 500}]}).status_code == 422
        assert client.post(url, json={"points": [{**base, "skin_temperature": 99}]}).status_code == 422

    def test_one_active_session(self, client):
        _start(client)
        assert client.post("/live/sessions", json={}).status_code == 409

    def test_active_endpoint_and_owner_view(self, client):
        started = _start(client)
        active = client.get("/live/sessions/active")
        assert active.status_code == 200
        assert active.json()["session"]["id"] == started["session"]["id"]
        assert active.json()["share_url"] == started["share_url"]
        assert client.get(f"/live/sessions/{started['session']['id']}").status_code == 200

    def test_no_active_session_is_404(self, client):
        assert client.get("/live/sessions/active").status_code == 404

    def test_cancel_returns_204_and_kills_link(self, client):
        started = _start(client)
        token = started["share_url"].rsplit("/live/", 1)[1]
        assert client.delete(f"/live/sessions/{started['session']['id']}").status_code == 204
        assert client.get(f"/public/live/{token}").status_code == 404

    def test_other_user_gets_404(self, db):
        owner = TestClient(_app(db))
        started = _start(owner)
        stranger = TestClient(_app(db, user_id=USER_ID + 1))
        session_id = started["session"]["id"]
        assert stranger.get(f"/live/sessions/{session_id}").status_code == 404
        assert stranger.post(f"/live/sessions/{session_id}/points", json=_PUSH).status_code == 404
        assert stranger.post(f"/live/sessions/{session_id}/stop").status_code == 404
        assert stranger.delete(f"/live/sessions/{session_id}").status_code == 404

    def test_rejects_bad_payloads(self, client, now):
        started = _start(client)
        url = f"/live/sessions/{started['session']['id']}/points"
        bad_lat = {"points": [{"recorded_at": now.isoformat(), "latitude": 120, "longitude": 0}]}
        assert client.post(url, json=bad_lat).status_code == 422
        assert client.post(url, json={"points": []}).status_code == 422
        too_many = {"points": [{**_PUSH["points"][0]}] * 201}
        assert client.post(url, json=too_many).status_code == 422
        assert client.post("/live/sessions/not-a-uuid/points", json=_PUSH).status_code == 422
        naive = {
            "points": [
                {"recorded_at": datetime.now(UTC).replace(tzinfo=None).isoformat(), "latitude": 1, "longitude": 1}
            ]
        }
        assert client.post(url, json=naive).status_code == 400


class TestPublicEndpoint:
    @pytest.mark.parametrize("token", ["garbage", "a" * 32 + ".b", "a" * 101])
    def test_forged_tokens_are_404_or_422_without_detail(self, client, token):
        response = client.get(f"/public/live/{token}")
        assert response.status_code in (404, 422)

    def test_requires_no_auth_dependencies(self):
        deps = [d.call for route in public_router.router.routes for d in route.dependant.dependencies]
        assert auth_deps.check_scopes not in deps
        assert auth_deps.get_sub_from_access_token not in deps


class TestContacts:
    def test_crud(self, client):
        created = client.post("/live/contacts", json={"name": "Ana", "email": "ana@example.com"})
        assert created.status_code == 201
        assert client.get("/live/contacts").json() == [created.json()]
        assert client.post("/live/contacts", json={"name": "Ana", "email": "ana@example.com"}).status_code == 409
        assert client.post("/live/contacts", json={"name": "Ana", "email": "not-an-email"}).status_code == 422
        assert client.delete(f"/live/contacts/{created.json()['id']}").status_code == 204
        assert client.get("/live/contacts").json() == []

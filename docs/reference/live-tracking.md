# Live tracking API reference

Real-time position sharing while a workout is recorded. A client starts a session, pushes points, and anyone with the share link can poll the session without logging in. Stopping the session kills the link and deletes the live points. No activity is created from the live data: the client records the workout itself and uploads it through the normal activity upload when it is done.

## Flow

1. `POST /api/v1/live/sessions` starts a session (scope `live:write`) and returns `share_url`. One active session per user. If SMTP is configured, the chosen contacts are emailed the link.
2. `POST /api/v1/live/sessions/{id}/points` pushes batches of up to 200 points. Resending a stored point is harmless.
3. `GET /api/v1/public/live/{token}` is the unauthenticated viewer endpoint. Add `?since=<iso time>` to receive only newer points. Forged, unknown, ended and expired links all answer the same 404.
4. `POST /api/v1/live/sessions/{id}/stop` ends the session, kills the link and deletes the live points. `DELETE /api/v1/live/sessions/{id}` removes the session entirely.

Contacts (the people emailed at start) are managed with `GET/POST /api/v1/live/contacts` and `DELETE /api/v1/live/contacts/{id}`.

A session that goes quiet for `LIVE_TRACKING_STALE_MINUTES` or outlives `LIVE_TRACKING_MAX_SESSION_HOURS` is ended by the scheduler, with the same result as a stop.

## Share links

The link is `{ENDURAIN_HOST}/live/<token>`. The token is `<session id>.<HMAC>`, derived from the session id and `SECRET_KEY`, so nothing is stored and the owner can always read the link back. Rotating `SECRET_KEY` invalidates links of running sessions.

## Settings

| Variable | Default | Description |
| --- | --- | --- |
| `LIVE_TRACKING_ENABLED` | `true` | When false, sessions cannot start and share links answer 404. |
| `LIVE_TRACKING_MAX_SESSION_HOURS` | `24` | Hard cap on a session's length. |
| `LIVE_TRACKING_STALE_MINUTES` | `30` | A session with no points for this long is ended. |
| `LIVE_TRACKING_MAX_CONTACTS` | `20` | Contacts per user. |

## Service

::: backend.app.modules.live_tracking.service
    handler: python
    options:
      docstring_style: google

## Schemas

::: backend.app.modules.live_tracking.schema
    handler: python
    options:
      docstring_style: google

## Events

::: backend.app.modules.live_tracking.events
    handler: python
    options:
      docstring_style: google

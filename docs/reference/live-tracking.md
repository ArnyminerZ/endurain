# Live tracking API reference

Real-time position sharing while a workout is recorded. A client starts a session, pushes points, and anyone with the share link can poll the session without logging in. Stopping the session kills the link and deletes the live points. No activity is created from the live data: the client records the workout itself and uploads it through the normal activity upload when it is done.

## Flow

1. `POST /api/v1/live/sessions` starts a session (scope `live:write`) and returns `share_url`. One active session per user. If SMTP is configured, the chosen contacts are emailed the link.
2. `POST /api/v1/live/sessions/{id}/points` pushes batches of up to 200 points. Resending a stored point is harmless.
3. `GET /api/v1/public/live/{token}` is the unauthenticated viewer endpoint. Add `?since=<iso time>` to receive only newer points. Forged, unknown, ended and expired links all answer the same 404.
4. `POST /api/v1/live/sessions/{id}/stop` ends the session, kills the link and deletes the live points. `DELETE /api/v1/live/sessions/{id}` removes the session entirely.

Contacts (the people emailed at start) are managed with `GET/POST /api/v1/live/contacts` and `DELETE /api/v1/live/contacts/{id}`.

A session that goes quiet for `LIVE_TRACKING_STALE_MINUTES` or outlives `LIVE_TRACKING_MAX_SESSION_HOURS` is ended by the scheduler, with the same result as a stop.

## Point quality

Besides the position, a point can say how good it is. All of these are optional and a viewer only shows what it gets.

| Field | Meaning |
| --- | --- |
| `position_source` | Where the position was measured: `gadget` (the watch's own GPS) or `phone`. |
| `satellites` | Satellites used for the fix. |
| `horizontal_accuracy` | Estimated horizontal accuracy of the fix, in meters. |
| `phone_signal_dbm` | The phone's mobile signal power in dBm (-150 to 0). |
| `phone_signal_type` | Which measurement `phone_signal_dbm` is: `rsrp` (LTE and 5G), `rssi` or `rscp` (3G). Required with `phone_signal_dbm`, and the other way round. |
| `phone_signal` | Deprecated 0-4 level, still accepted from older clients. |

The viewer turns the signal into bars the way a phone's status bar does (the same dBm means different things for each kind of measurement, which is why the type is sent), and rates the position as precise, approximate or rough from the accuracy, or from the satellite count when no accuracy is sent.

## Share links

The link is `{ENDURAIN_HOST}/live/<token>`. The token is the session id (32 hex characters) followed directly by an HMAC (43 characters), derived from the session id and `SECRET_KEY`, so nothing is stored and the owner can always read the link back. Rotating `SECRET_KEY` invalidates links of running sessions.

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

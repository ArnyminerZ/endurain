"""Live tracking module: real-time position sharing while a workout is recorded.

An athlete starts a live session, a client pushes position updates, and anyone
holding the share link can poll the session without logging in. Stopping the
session kills the link and turns the recorded points into a normal activity
through the ingestion pipeline; the live points are then deleted.

Other modules consume it only through ``schema``, ``constants`` and ``events``;
``__init__`` exports nothing.
"""

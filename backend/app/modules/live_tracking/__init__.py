"""Live tracking module: real-time position sharing while a workout is recorded.

An athlete starts a live session, a client pushes position updates, and anyone
holding the share link can poll the session without logging in. Stopping the
session kills the link and deletes the live points. Nothing is turned into an
activity: the client uploads its own recording through the normal upload.

Other modules consume it only through ``schema``, ``constants`` and ``events``;
``__init__`` exports nothing.
"""

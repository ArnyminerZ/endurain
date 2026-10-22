"""Stateless share tokens for live sessions.

A token is ``<session uuid hex>.<mac>`` where the mac is an HMAC of the session id
under the server secret. Nothing secret is stored: the server can re-derive the
link for the owner, and a guessed or forged token fails the mac check. The link
dies because the session ends, not because a token is deleted.
"""

import base64
import hashlib
import hmac
import uuid

_MAC_CONTEXT = b"endurain.live_tracking.share.v1:"


def _mac(session_id: str, secret: str) -> str:
    """Return the URL-safe mac for a session id.

    Args:
        session_id: The session UUID string.
        secret: The server secret the mac is keyed with.

    Returns:
        A 43-character URL-safe base64 mac.
    """
    digest = hmac.new(secret.encode(), _MAC_CONTEXT + session_id.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def build_token(session_id: str, secret: str) -> str:
    """Build the share token for a session.

    Args:
        session_id: The session UUID string.
        secret: The server secret the mac is keyed with.

    Returns:
        The token to place in the public link.
    """
    return f"{uuid.UUID(session_id).hex}.{_mac(session_id, secret)}"


def parse_token(token: str, secret: str) -> str | None:
    """Return the session id a token authorises, or ``None`` when it is invalid.

    Args:
        token: The token from the public link.
        secret: The server secret the mac is keyed with.

    Returns:
        The session UUID string, or ``None`` for any malformed or forged token.
    """
    head, separator, mac = token.partition(".")
    if not separator or len(head) != 32:
        return None
    try:
        session_id = str(uuid.UUID(hex=head))
    except ValueError:
        return None
    if not hmac.compare_digest(mac.encode(), _mac(session_id, secret).encode()):
        return None
    return session_id

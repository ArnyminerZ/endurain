import uuid

import modules.live_tracking.share_token as share_token

SECRET = "unit-test-secret"


class TestShareToken:
    def test_roundtrip(self):
        session_id = str(uuid.uuid4())
        token = share_token.build_token(session_id, SECRET)
        assert share_token.parse_token(token, SECRET) == session_id

    def test_wrong_secret_is_rejected(self):
        token = share_token.build_token(str(uuid.uuid4()), SECRET)
        assert share_token.parse_token(token, "another-secret") is None

    def test_tampered_session_is_rejected(self):
        token = share_token.build_token(str(uuid.uuid4()), SECRET)
        _, _, mac = token.partition(".")
        forged = f"{uuid.uuid4().hex}.{mac}"
        assert share_token.parse_token(forged, SECRET) is None

    def test_garbage_is_rejected(self):
        for token in ("", "abc", "x" * 32, f"{'z' * 32}.mac", "no-dot-here"):
            assert share_token.parse_token(token, SECRET) is None

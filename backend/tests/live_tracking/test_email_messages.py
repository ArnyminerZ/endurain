import modules.live_tracking.email_messages as email_messages


class TestLiveSessionStartedEmail:
    def test_builds_all_parts(self):
        subject, html, text = email_messages.get_live_session_started_email(
            "Ana", "Arnau", "Long run", "https://x.test/live/abc", "https://x.test", "en"
        )
        assert "Arnau" in subject
        assert "https://x.test/live/abc" in html
        assert "https://x.test/live/abc" in text
        assert "Long run" in text

    def test_user_text_is_escaped_in_html(self):
        _, html, _ = email_messages.get_live_session_started_email(
            "<b>Ana</b>", "A&B", "<i>x</i>", "https://x.test/live/abc", "https://x.test", "en"
        )
        assert "<b>Ana</b>" not in html
        assert "A&amp;B" in html

    def test_localised_and_unnamed_workout(self):
        subject, _, text = email_messages.get_live_session_started_email(
            "Ana", "Arnau", None, "https://x.test/live/abc", "https://x.test", "es"
        )
        assert "directo" in subject
        assert "{workout}" not in text

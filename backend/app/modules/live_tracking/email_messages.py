"""Email message builders for live tracking notifications."""

import html
from urllib.parse import quote as url_quote

import core.email_templates as core_email_templates
import core.i18n as core_i18n


def get_live_session_started_email(
    contact_name: str,
    athlete_name: str,
    workout_name: str | None,
    live_link: str,
    frontend_host: str,
    locale: str | None = None,
) -> tuple[str, str, str]:
    """Build the localized "live tracking started" email.

    Args:
        contact_name: The recipient's display name.
        athlete_name: The athlete's name.
        workout_name: Optional workout name.
        live_link: The public live link.
        frontend_host: Base URL of the frontend, used in the footer.
        locale: Preferred locale code; falls back to ``"en"``.

    Returns:
        A 3-tuple of (subject, html_content, text_content).
    """
    safe_contact = html.escape(contact_name)
    safe_athlete = html.escape(athlete_name)

    def tr(key: str, **kwargs: str) -> str:
        return core_i18n.t(key, locale, **kwargs)

    subject = tr("live_tracking.subject", athlete=athlete_name)
    heading = tr("live_tracking.heading")
    intro_key = "live_tracking.intro_named" if workout_name else "live_tracking.intro"
    intro = tr(intro_key, athlete=safe_athlete, workout=html.escape(workout_name or ""))
    plain_intro = tr(intro_key, athlete=athlete_name, workout=workout_name or "")
    cta = tr("live_tracking.cta")
    notice = tr("live_tracking.notice")
    copy_link = tr("common.copy_link")

    color = core_email_templates.LINK_COLOR_PRIMARY
    safe_link = html.escape(url_quote(live_link, safe=":/?=&%#@"), quote=True)

    body_inner = f"""
            <p>{tr("live_tracking.greeting", name=safe_contact)}</p>
            <p>{intro}</p>
            <div style="text-align: center; margin: 30px 0;">
                <a
                    href="{safe_link}"
                    style="background-color: {color}; color: #ffffff;
                    padding: 12px 30px; text-decoration: none;
                    border-radius: 8px; display: inline-block;
                    font-weight: 600;"
                >{cta}</a>
            </div>
            <p>{notice}</p>
            <p>{copy_link}</p>
            <p style="word-break: break-all; color: {color};">{safe_link}</p>"""

    html_content = core_email_templates.wrap_email(
        locale=locale,
        subject=subject,
        heading=heading,
        body_inner=body_inner,
        frontend_host=frontend_host,
        link_color=color,
    )

    labels = core_i18n.common_labels(locale)
    text_content = (
        f"{tr('live_tracking.greeting', name=contact_name)}\n\n"
        f"{plain_intro}\n"
        f"{live_link}\n\n"
        f"{notice}\n\n"
        f"{labels['best_regards']}\n"
        f"{labels['team']}"
    )
    return subject, html_content, text_content

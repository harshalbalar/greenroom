"""
Email service — sends transactional emails via Resend.

Handles: new job alerts, morning briefs, application status updates.
Falls back silently if RESEND_API_KEY is not configured (so the app
works without email in development).

Setup:
    1. Sign up at https://resend.com (free: 100 emails/day)
    2. Get your API key from the dashboard
    3. Add RESEND_API_KEY=re_xxxxx to .env
    4. (Optional) Verify a custom domain for FROM_EMAIL
       Default: onboarding@resend.dev (Resend's sandbox — works immediately)
"""

import resend
from config import settings


def _is_configured() -> bool:
    return bool(settings.RESEND_API_KEY)


def _init():
    """Set the API key. Called before each send."""
    resend.api_key = settings.RESEND_API_KEY


def send_new_jobs_alert(to_email: str, user_name: str, new_count: int, top_jobs: list[dict]):
    """Email: new jobs found after an auto-scan."""
    if not _is_configured():
        return

    _init()

    jobs_html = ""
    for j in top_jobs[:5]:
        score = j.get("overall_score", "?")
        jobs_html += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;">
                <strong>{j.get('title','')}</strong><br>
                <span style="color:#666;">{j.get('company','')}</span>
            </td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;">
                <span style="background:#7B6CF6;color:#fff;padding:2px 8px;border-radius:12px;font-size:13px;">{score}</span>
            </td>
        </tr>"""

    html = f"""
    <div style="font-family:Inter,system-ui,sans-serif;max-width:560px;margin:0 auto;color:#1a1a2e;">
        <div style="background:linear-gradient(135deg,#7B6CF6,#E966A0);padding:24px;border-radius:12px 12px 0 0;">
            <h1 style="color:#fff;margin:0;font-size:22px;">🔭 {new_count} new job{'' if new_count == 1 else 's'} found</h1>
        </div>
        <div style="background:#fff;padding:24px;border:1px solid #eee;border-top:none;border-radius:0 0 12px 12px;">
            <p>Hey {user_name or 'there'},</p>
            <p>Greenroom just scanned and found <strong>{new_count} new job{'' if new_count == 1 else 's'}</strong> matching your preferences.</p>
            {f'''
            <table style="width:100%;border-collapse:collapse;margin:16px 0;">
                <tr style="background:#f8f8fc;">
                    <th style="padding:8px 12px;text-align:left;font-size:13px;color:#666;">Top matches</th>
                    <th style="padding:8px 12px;text-align:center;font-size:13px;color:#666;">Score</th>
                </tr>
                {jobs_html}
            </table>
            ''' if top_jobs else ''}
            <p style="margin-top:20px;">
                <a href="{settings.DATABASE_URL and 'https://greenroom-8wwb.onrender.com' or 'http://localhost:3000'}" style="background:#7B6CF6;color:#fff;padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:500;">Open Greenroom</a>
            </p>
        </div>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": [to_email],
            "subject": f"🔭 {new_count} new job{'' if new_count == 1 else 's'} found — Greenroom",
            "html": html,
        })
    except Exception as e:
        print(f"  [Email] Failed to send new jobs alert: {e}")


def send_morning_brief(
    to_email: str,
    user_name: str,
    new_since_yesterday: int,
    top_jobs: list[dict],
    stats: dict,
):
    """Email: daily morning brief with job summary and application stats."""
    if not _is_configured():
        return

    _init()

    jobs_html = ""
    for j in top_jobs[:5]:
        score = j.get("overall_score", "?")
        jobs_html += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;">
                <strong>{j.get('title','')}</strong><br>
                <span style="color:#666;">{j.get('company','')}</span>
            </td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;">
                <span style="background:#7B6CF6;color:#fff;padding:2px 8px;border-radius:12px;font-size:13px;">{score}</span>
            </td>
        </tr>"""

    ready = stats.get("ready", 0)
    applied = stats.get("applied", 0)
    interviewing = stats.get("interviewing", 0)

    html = f"""
    <div style="font-family:Inter,system-ui,sans-serif;max-width:560px;margin:0 auto;color:#1a1a2e;">
        <div style="background:linear-gradient(135deg,#0d0b1e,#1a1a2e);padding:24px;border-radius:12px 12px 0 0;">
            <h1 style="color:#fff;margin:0;font-size:22px;">☀️ Your morning brief</h1>
            <p style="color:rgba(255,255,255,0.6);margin:6px 0 0;font-size:14px;">Here's what's happening in your job search.</p>
        </div>
        <div style="background:#fff;padding:24px;border:1px solid #eee;border-top:none;border-radius:0 0 12px 12px;">
            <p>Good morning{(', ' + user_name) if user_name else ''}!</p>

            <div style="display:flex;gap:12px;margin:16px 0;">
                <div style="flex:1;background:#f0fdf4;padding:14px;border-radius:10px;text-align:center;">
                    <div style="font-size:24px;font-weight:700;color:#16a34a;">{new_since_yesterday}</div>
                    <div style="font-size:11px;color:#666;margin-top:2px;">new jobs</div>
                </div>
                <div style="flex:1;background:#faf5ff;padding:14px;border-radius:10px;text-align:center;">
                    <div style="font-size:24px;font-weight:700;color:#7B6CF6;">{ready}</div>
                    <div style="font-size:11px;color:#666;margin-top:2px;">ready to send</div>
                </div>
                <div style="flex:1;background:#fffbeb;padding:14px;border-radius:10px;text-align:center;">
                    <div style="font-size:24px;font-weight:700;color:#d97706;">{applied}</div>
                    <div style="font-size:11px;color:#666;margin-top:2px;">applied</div>
                </div>
                <div style="flex:1;background:#fef2f2;padding:14px;border-radius:10px;text-align:center;">
                    <div style="font-size:24px;font-weight:700;color:#ef4444;">{interviewing}</div>
                    <div style="font-size:11px;color:#666;margin-top:2px;">interviews</div>
                </div>
            </div>

            {f'''
            <h3 style="font-size:14px;color:#333;margin:20px 0 8px;">Top unprepped matches</h3>
            <table style="width:100%;border-collapse:collapse;">
                {jobs_html}
            </table>
            ''' if top_jobs else '<p style="color:#666;">No new matches to show today.</p>'}

            <p style="margin-top:20px;">
                <a href="https://greenroom-8wwb.onrender.com" style="background:linear-gradient(135deg,#7B6CF6,#E966A0);color:#fff;padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:500;">Open Greenroom</a>
            </p>
        </div>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": [to_email],
            "subject": f"☀️ Morning brief — {new_since_yesterday} new jobs — Greenroom",
            "html": html,
        })
    except Exception as e:
        print(f"  [Email] Failed to send morning brief: {e}")

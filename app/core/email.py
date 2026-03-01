"""Async email service for sending prayer requests using Gmail SMTP (smtplib).
GitHub Actions does not block SMTP ports — works perfectly with Gmail on port 465.
"""
import asyncio
import logging
import smtplib
import ssl
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Optional, Dict, Any

from ..settings import DEFAULT_RECIPIENT, EMAIL_USER, EMAIL_APP_PASSWORD

# Fixed sender identity
SENDER_EMAIL = "rachelyayn4734@gmail.com"
SENDER_NAME = "RunPrayer"
FROM_ADDRESS = formataddr((SENDER_NAME, SENDER_EMAIL))

log = logging.getLogger(__name__)


def build_plain_message(name: str, request: Optional[str], sent_at: Optional[str] = None) -> str:
    """Build plain text prayer message."""
    prayer_text = request or "למציאת עבודה טובה בקלות ובמהירות"
    timestamp = sent_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"""שלום לכולן,

היום מתפללים על *{name}* – *{prayer_text}*.

ובנוסף – לרפואת הפצועים ולשמירה על החיילים.

🙏 בואו נעצור לרגע ונאמר פרק תהילים קצר.

---
Sent at: {timestamp}
"""
    return msg

def build_html_message(name: str, request: Optional[str], sent_at: Optional[str] = None) -> str:
    """Build HTML prayer message with Psalm 23."""
    prayer_text = request or "למציאת עבודה טובה בקלות ובמהירות"
    timestamp = sent_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    psalm_text = """
<div style="text-align:right;">
<span style="direction:rtl; display:inline-block;">{א} מִזְמוֹר לְדָוִד יְהוָה רֹעִי לֹא אֶחְסָר.</span><br>
<span style="direction:rtl; display:inline-block;">{ב} בִּנְאוֹת דֶּשֶׁא יַרְבִּיצֵנִי עַל-מֵי מְנֻחוֹת יְנַהֲלֵנִי.</span><br>
<span style="direction:rtl; display:inline-block;">{ג} נַפְשִׁי יְשׁוֹבֵב יַנְחֵנִי בְמַעְגְּלֵי-צֶדֶק לְמַעַן שְׁמוֹ.</span><br>
<span style="direction:rtl; display:inline-block;">{ד} גַּם כִּי-אֵלֵךְ בְּגֵיא צַלְמָוֶת לֹא-אִירָא רָע כִּי-אַתָּה עִמָּדִי שִׁבְטְךָ וּמִשְׁעַנְתֶּךָ הֵמָּה יְנַחֲמֻנִי.</span><br>
<span style="direction:rtl; display:inline-block;">{ה} תַּעֲרֹךְ לְפָנַי שֻׁלְחָן נֶגֶד צֹרְרָי דִּשַּׁנְתָּ בַשֶּׁמֶן רֹאשִׁי כּוֹסִי רְוָיָה.</span><br>
<span style="direction:rtl; display:inline-block;">{ו} אַךְ טוֹב וָחֶסֶד יִרְדְּפוּנִי כָּל-יְמֵי חַיָּי וְשַׁבְתִּי בְּבֵית-יְהוָה לְאֹרֶךְ יָמִים.</span><br>
</div>
    """
    return f"""<html>
<body>
<div dir="rtl">
<p style="text-align:right;"> שלום לכולן,<br><br>
    היום מתפללים על <strong>{name}</strong> – <strong>{prayer_text}</strong><br><br>
    ובנוסף – לרפואת הפצועים,  ולשמירה על החיילים.<br><br>
    🙏 בואו נעצור לרגע ונאמר פרק תהילים קצר.<br>
    לנוחיותכן, מצרפת פרק תהילים שמסוגל לפרנסה טובה:<br><br>
</p>
<div style="font-size:14px; text-align:right;">
{psalm_text}
</div>
<p style="text-align:right;">
    אם תוכלנה לסמן ❤ על ההודעה כדי שאוכל לדעת שהשתתפתן.<br><br>
    תזכו למצוות, מעריכות מאד!<br>
</p>
</div>
<p style="font-size:11px; color:#aaa; text-align:left; direction:ltr;">
    Daily ID: {timestamp}
</p>
</body>
</html>"""

def _send_email_smtp(
    recipient: str,
    subject: str,
    plain_content: str,
    html_content: str,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Send email via Gmail SMTP SSL on port 465.
    Works on GitHub Actions (SMTP ports are not blocked).
    """
    if not EMAIL_USER:
        log.error("EMAIL_USER not configured")
        return {"success": False, "error": "EMAIL_USER not configured", "attempt": 0}
    if not EMAIL_APP_PASSWORD:
        log.error("EMAIL_APP_PASSWORD not configured")
        return {"success": False, "error": "EMAIL_APP_PASSWORD not configured", "attempt": 0}

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = FROM_ADDRESS
    msg["To"] = recipient
    msg.attach(MIMEText(plain_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    last_error: Optional[str] = None
    for attempt in range(1, max_retries + 1):
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(EMAIL_USER, EMAIL_APP_PASSWORD)
                server.sendmail(SENDER_EMAIL, recipient, msg.as_string())
            log.info("[Gmail SMTP] ✅ Email sent to %s on attempt %d", recipient, attempt)
            return {"success": True, "attempt": attempt}
        except smtplib.SMTPAuthenticationError as e:
            log.error("[Gmail SMTP] Authentication failed: %s", e)
            return {"success": False, "error": f"Authentication failed: {e}", "attempt": attempt}
        except Exception as e:
            last_error = str(e)
            log.warning("[Gmail SMTP] Attempt %d/%d failed: %s", attempt, max_retries, last_error)
            if attempt < max_retries:
                time.sleep(2 ** (attempt - 1))

    return {"success": False, "error": f"Failed after {max_retries} attempts: {last_error}", "attempt": max_retries}


async def send_email(
    name: str,
    request: Optional[str],
    recipient: Optional[str] = None,
    prayer_id: Optional[int] = None,
    max_retries: int = 3
) -> bool:
    """
    Async email sending via Gmail SMTP with retry logic.
    Runs the blocking SMTP call in a thread so the event loop stays free.
    """
    if not EMAIL_USER or not EMAIL_APP_PASSWORD:
        log.error("Missing Gmail credentials: EMAIL_USER and/or EMAIL_APP_PASSWORD")
        return False

    recipient = recipient or DEFAULT_RECIPIENT
    if not recipient:
        log.error("No recipient specified and DEFAULT_RECIPIENT not set")
        return False

    now = datetime.now()
    sent_at = now.strftime("%Y-%m-%d %H:%M:%S")
    day_name = now.strftime("%A")
    date_str = now.strftime("%b %d, %Y")
    subject = f"Daily Prayer - {day_name}, {date_str}"

    plain_content = build_plain_message(name, request, sent_at)
    html_content = build_html_message(name, request, sent_at)

    log.info("[Gmail SMTP] Preparing email | Subject: '%s' | To: %s | Prayer: %s", subject, recipient, name)

    try:
        result = await asyncio.to_thread(
            _send_email_smtp,
            recipient, subject, plain_content, html_content, max_retries,
        )
        if result["success"]:
            log.info("Email sent to %s for prayer: %s (ID: %s) on attempt %d",
                     recipient, name, prayer_id or "N/A", result["attempt"])
            return True
        else:
            log.error("Email failed to %s for prayer: %s (ID: %s) - %s",
                      recipient, name, prayer_id or "N/A", result["error"])
            return False
    except Exception as e:
        log.error("Gmail SMTP error for prayer %s (ID: %s): %s", name, prayer_id, e, exc_info=True)
        return False


async def send_email_batch(
    recipients: list[str],
    name: str,
    request: Optional[str],
    prayer_id: Optional[int] = None
) -> Dict[str, bool]:
    """Send email to multiple recipients concurrently."""
    if not recipients:
        return {}

    log.info("Sending prayer email to %d recipients: %s", len(recipients), name)

    tasks = [send_email(name, request, recipient, prayer_id) for recipient in recipients]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    result_map = {}
    for recipient, result in zip(recipients, results):
        if isinstance(result, Exception):
            log.error("Email to %s failed with exception: %s", recipient, result)
            result_map[recipient] = False
        else:
            result_map[recipient] = result

    success_count = sum(1 for success in result_map.values() if success)
    log.info("Email batch complete: %d/%d successful", success_count, len(recipients))
    return result_map


def validate_email_config() -> bool:
    """Validate Gmail SMTP configuration."""
    missing = []
    if not EMAIL_USER:
        missing.append("EMAIL_USER")
    if not EMAIL_APP_PASSWORD:
        missing.append("EMAIL_APP_PASSWORD")
    if missing:
        log.error(f"Missing email configuration: {', '.join(missing)}")
        return False
    return True


# ---------------------------------------------------------------------------
# TEMPORARY TEST — remove after verifying email delivery
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    async def _test():
        log.info("=== TEST: Sending a prayer email via Gmail SMTP ===")
        success = await send_email(
            name="Test Person",
            request="למציאת עבודה טובה בקלות ובמהירות",
            recipient=os.getenv("DEFAULT_RECIPIENT"),
        )
        if success:
            log.info("✅ Test email sent successfully!")
        else:
            log.error("❌ Test email failed – check EMAIL_USER and EMAIL_APP_PASSWORD.")
        return success

    result = asyncio.run(_test())
    sys.exit(0 if result else 1)

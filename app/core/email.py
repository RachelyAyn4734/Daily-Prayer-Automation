"""Async email service for sending prayer requests using Resend HTTP API.
Migrated from Gmail SMTP (blocked by Render) to Resend HTTPS API.
"""
import asyncio
import logging
import resend
from datetime import datetime
from typing import Optional, Dict, Any

from ..settings import DEFAULT_RECIPIENT, RESEND_API_KEY

# Fixed sender identity — must be a verified sender in Resend console
SENDER_EMAIL = "rachelyayn4734@gmail.com"
SENDER_NAME = "RunPrayer"
FROM_ADDRESS = f"{SENDER_NAME} <{SENDER_EMAIL}>"

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

def _send_email_resend(
    recipient: str,
    subject: str,
    plain_content: str,
    html_content: str,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Send email via Resend HTTPS API.
    Works on Render free tier (no blocked ports).
    """
    if not RESEND_API_KEY:
        log.error("RESEND_API_KEY not configured")
        return {"success": False, "error": "RESEND_API_KEY not configured", "attempt": 0}

    resend.api_key = RESEND_API_KEY

    last_error: Optional[str] = None
    for attempt in range(1, max_retries + 1):
        try:
            params: resend.Emails.SendParams = {
                "from": FROM_ADDRESS,
                "to": [recipient],
                "subject": subject,
                "html": html_content,
                "text": plain_content,
            }
            response = resend.Emails.send(params)
            log.info("[Resend] ✅ Email sent to %s on attempt %d (id: %s)", recipient, attempt, response.get("id"))
            return {"success": True, "attempt": attempt}
        except Exception as e:
            last_error = str(e)
            log.warning("[Resend] Attempt %d/%d failed: %s", attempt, max_retries, last_error)
            if attempt < max_retries:
                import time
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
    Async email sending via Resend HTTPS API with retry logic.

    Args:
        name: Prayer name
        request: Prayer request text
        recipient: Email recipient (defaults to DEFAULT_RECIPIENT)
        prayer_id: Database prayer ID for logging
        max_retries: Number of retry attempts

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    if not RESEND_API_KEY:
        log.error("Missing RESEND_API_KEY")
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

    log.info("[Resend] Preparing email | Subject: '%s' | To: %s | Prayer: %s", subject, recipient, name)

    try:
        result = await asyncio.to_thread(
            _send_email_resend,
            recipient,
            subject,
            plain_content,
            html_content,
            max_retries,
        )

        if result["success"]:
            log.info("Email sent successfully to %s for prayer: %s (ID: %s) on attempt %d",
                     recipient, name, prayer_id or "N/A", result["attempt"])
            return True
        else:
            log.error("Email failed to %s for prayer: %s (ID: %s) - %s",
                      recipient, name, prayer_id or "N/A", result["error"])
            return False

    except Exception as e:
        log.error("Resend email error for prayer %s (ID: %s): %s", name, prayer_id, e, exc_info=True)
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
    """Validate email configuration is properly set for Resend."""
    if not RESEND_API_KEY:
        log.error("Missing email configuration: RESEND_API_KEY")
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
        log.info("=== TEST: Sending a prayer email via Resend ===")
        success = await send_email(
            name="Test Person",
            request="למציאת עבודה טובה בקלות ובמהירות",
            recipient=os.getenv("DEFAULT_RECIPIENT"),
        )
        if success:
            log.info("✅ Test email sent successfully!")
        else:
            log.error("❌ Test email failed – check RESEND_API_KEY and sender verification.")
        return success

    result = asyncio.run(_test())
    sys.exit(0 if result else 1)

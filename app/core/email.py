"""
Async email service for sending prayer requests.
Consolidated and optimized from prayer_logic/prayers_file.py and other email logic.
"""
import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Dict, Any
import concurrent.futures
from ..settings import SENDER_EMAIL, SENDER_PASSWORD, DEFAULT_RECIPIENT

log = logging.getLogger(__name__)

# Thread pool executor for blocking SMTP operations
email_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="email-sender")

def build_plain_message(name: str, request: Optional[str]) -> str:
    """Build plain text prayer message."""
    prayer_text = request or "למציאת עבודה טובה בקלות ובמהירות"
    msg = f"""שלום לכולן,

היום מתפללים על *{name}* – *{prayer_text}*.

ובנוסף – לרפואת הפצועים ולשמירה על החיילים.

🙏 בואו נעצור לרגע ונאמר פרק תהילים קצר.
"""
    return msg

def build_html_message(name: str, request: Optional[str]) -> str:
    """Build HTML prayer message with Psalm 23."""
    prayer_text = request or "למציאת עבודה טובה בקלות ובמהירות"
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
<p style="text-align:right;direction:rtl;"> שלום לכולן,<br><br>
    היום מתפללים על <strong>{name}</strong> – <strong>{prayer_text}</strong><br><br>
    ובנוסף – לרפואת הפצועים,  ולשמירה על החיילים.<br><br>
    🙏 בואו נעצור לרגע ונאמר פרק תהילים קצר.<br>
    לנוחיותכן, מצרפת פרק תהילים שמסוגל לפרנסה טובה:<br><br>
</p>
<div style="font-size:14px; text-align:right; direction:rtl;">
{psalm_text}
</div>
<p style="text-align:right;direction:rtl;">
    אם תוכלנה לסמן ❤ על ההודעה כדי שאוכל לדעת שהשתתפתן.<br><br>
    תזכו למצוות, מעריכות מאד!<br>
</p>
</body>
</html>"""

def _send_email_sync(
    sender_email: str,
    sender_password: str,
    recipient: str,
    message: MIMEMultipart,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Synchronous email sending with retry logic.
    This runs in a thread pool to avoid blocking the event loop.
    Uses port 465 with SSL for better cloud environment compatibility.
    """
    for attempt in range(max_retries):
        try:
            # Use SMTP_SSL on port 465 for implicit SSL (better for cloud environments)
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient, message.as_string())
            
            return {"success": True, "attempt": attempt + 1}
            
        except smtplib.SMTPAuthenticationError as e:
            log.error("SMTP Authentication failed: %s", e)
            return {"success": False, "error": f"Authentication failed: {e}", "attempt": attempt + 1}
            
        except smtplib.SMTPRecipientsRefused as e:
            log.error("SMTP Recipients refused: %s", e)
            return {"success": False, "error": f"Recipients refused: {e}", "attempt": attempt + 1}
            
        except (smtplib.SMTPException, ConnectionError, TimeoutError) as e:
            log.warning("SMTP attempt %d/%d failed: %s", attempt + 1, max_retries, e)
            if attempt < max_retries - 1:
                asyncio.sleep(2 ** attempt)  # Exponential backoff
            continue
            
        except Exception as e:
            log.error("Unexpected email error on attempt %d: %s", attempt + 1, e, exc_info=True)
            return {"success": False, "error": f"Unexpected error: {e}", "attempt": attempt + 1}
    
    return {"success": False, "error": f"Failed after {max_retries} attempts", "attempt": max_retries}

async def send_email(
    name: str,
    request: Optional[str],
    recipient: Optional[str] = None,
    prayer_id: Optional[int] = None,
    max_retries: int = 3
) -> bool:
    """
    Async email sending with retry logic and proper error handling.
    
    Args:
        name: Prayer name
        request: Prayer request text
        recipient: Email recipient (defaults to DEFAULT_RECIPIENT)
        prayer_id: Database prayer ID for logging
        max_retries: Number of retry attempts
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        log.error("Missing email credentials: SENDER_EMAIL or SENDER_PASSWORD")
        return False

    recipient = recipient or DEFAULT_RECIPIENT
    if not recipient:
        log.error("No recipient specified and DEFAULT_RECIPIENT not set")
        return False

    # Prepare email message
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient
    msg["Subject"] = "Today's Prayer Request"

    # Attach both plain and HTML versions
    msg.attach(MIMEText(build_plain_message(name, request), "plain", _charset="utf-8"))
    msg.attach(MIMEText(build_html_message(name, request), "html", _charset="utf-8"))

    try:
        # Run blocking SMTP operation in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            email_executor,
            _send_email_sync,
            SENDER_EMAIL,
            SENDER_PASSWORD,
            recipient,
            msg,
            max_retries
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
        error_msg = f"Async email error for prayer {name} (ID: {prayer_id}): {e}"
        log.error(error_msg, exc_info=True)
        return False

async def send_email_batch(
    recipients: list[str], 
    name: str, 
    request: Optional[str],
    prayer_id: Optional[int] = None
) -> Dict[str, bool]:
    """
    Send email to multiple recipients concurrently.
    
    Returns:
        Dict mapping recipient emails to success status
    """
    if not recipients:
        return {}
    
    log.info("Sending prayer email to %d recipients: %s", len(recipients), name)
    
    # Send emails concurrently
    tasks = [
        send_email(name, request, recipient, prayer_id)
        for recipient in recipients
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Map results to recipients
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
    """Validate email configuration is properly set."""
    missing = []
    
    if not SENDER_EMAIL:
        missing.append("SENDER_EMAIL")
    if not SENDER_PASSWORD:
        missing.append("SENDER_PASSWORD")
    
    if missing:
        log.error(f"Missing email configuration: {', '.join(missing)}")
        return False
    
    return True
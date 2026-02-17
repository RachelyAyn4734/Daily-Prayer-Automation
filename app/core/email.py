"""
"""Async email service for sending prayer requests using SendGrid.
Consolidated and optimized from prayer_logic/prayers_file.py and other email logic.
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent
from ..settings import SENDER_EMAIL, DEFAULT_RECIPIENT, SENDGRID_API_KEY

log = logging.getLogger(__name__)

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

async def _send_email_sendgrid(
    sender_email: str,
    recipient: str,
    subject: str,
    plain_content: str,
    html_content: str,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Send email using SendGrid API with retry logic.
    SendGrid uses HTTPS API calls which work reliably on cloud platforms.
    """
    if not SENDGRID_API_KEY:
        log.error("SENDGRID_API_KEY not configured")
        return {"success": False, "error": "SendGrid API key not configured", "attempt": 0}
    
    # Create SendGrid message
    message = Mail(
        from_email=Email(sender_email),
        to_emails=To(recipient),
        subject=subject,
        plain_text_content=Content("text/plain", plain_content),
        html_content=HtmlContent(html_content)
    )
    
    for attempt in range(max_retries):
        try:
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            response = sg.send(message)
            
            if response.status_code in (200, 201, 202):
                log.info("SendGrid email sent successfully (status: %d)", response.status_code)
                return {"success": True, "attempt": attempt + 1, "status_code": response.status_code}
            else:
                log.warning("SendGrid returned status %d on attempt %d", response.status_code, attempt + 1)
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                continue
                
        except Exception as e:
            error_msg = str(e)
            log.warning("SendGrid attempt %d/%d failed: %s", attempt + 1, max_retries, error_msg)
            
            # Check for specific SendGrid errors
            if hasattr(e, 'status_code'):
                if e.status_code == 401:
                    return {"success": False, "error": "Invalid SendGrid API key", "attempt": attempt + 1}
                elif e.status_code == 403:
                    return {"success": False, "error": "SendGrid API access forbidden", "attempt": attempt + 1}
            
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            continue
    
    return {"success": False, "error": f"Failed after {max_retries} attempts", "attempt": max_retries}

async def send_email(
    name: str,
    request: Optional[str],
    recipient: Optional[str] = None,
    prayer_id: Optional[int] = None,
    max_retries: int = 3
) -> bool:
    """
    Async email sending via SendGrid with retry logic and proper error handling.
    
    Args:
        name: Prayer name
        request: Prayer request text
        recipient: Email recipient (defaults to DEFAULT_RECIPIENT)
        prayer_id: Database prayer ID for logging
        max_retries: Number of retry attempts
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    if not SENDGRID_API_KEY:
        log.error("Missing SendGrid API key: SENDGRID_API_KEY")
        return False
    
    if not SENDER_EMAIL:
        log.error("Missing sender email: SENDER_EMAIL")
        return False

    recipient = recipient or DEFAULT_RECIPIENT
    if not recipient:
        log.error("No recipient specified and DEFAULT_RECIPIENT not set")
        return False

    # Build email content
    plain_content = build_plain_message(name, request)
    html_content = build_html_message(name, request)
    subject = "Today's Prayer Request"

    try:
        result = await _send_email_sendgrid(
            sender_email=SENDER_EMAIL,
            recipient=recipient,
            subject=subject,
            plain_content=plain_content,
            html_content=html_content,
            max_retries=max_retries
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
        error_msg = f"SendGrid email error for prayer {name} (ID: {prayer_id}): {e}"
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
    """Validate email configuration is properly set for SendGrid."""
    missing = []
    
    if not SENDER_EMAIL:
        missing.append("SENDER_EMAIL")
    if not SENDGRID_API_KEY:
        missing.append("SENDGRID_API_KEY")
    
    if missing:
        log.error(f"Missing email configuration: {', '.join(missing)}")
        return False
    
    return True
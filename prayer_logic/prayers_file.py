import argparse
import logging
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        pass

# Optional Selenium / webdriver for WhatsApp Web automation
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
except Exception:
    webdriver = None

# ⬅⬅⬅ imports פנימיים – תמיד יחסיים
from .prayer_utils import (
    load_prayers,
    load_prayers_with_phone,
)

# ----------------------------
# Logging
# ----------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ----------------------------
# Types
# ----------------------------
PrayersDict = Dict[str, Dict]  # {"1": {"name":..., "request":...}}

# ----------------------------
# State helpers
# ----------------------------
def read_text_int(path: Path, default: int = 0) -> int:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except Exception:
        return default

def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

# ----------------------------
# Prayer iteration logic
# ----------------------------
def max_index(prayers: PrayersDict) -> int:
    return max(int(k) for k in prayers.keys())

def find_index_by_name(name: str, prayers: PrayersDict) -> Optional[int]:
    for k, v in prayers.items():
        if v.get("name") == name:
            return int(k)
    return None

def next_existing_index(start: int, prayers: PrayersDict, max_idx: int) -> int:
    if start < 1 or start > max_idx:
        start = 1
    idx = start
    for _ in range(max_idx):
        if str(idx) in prayers:
            return idx
        idx += 1
        if idx > max_idx:
            idx = 1
    return 1

def process_next_prayer(
    current_index: int,
    prayers: PrayersDict,
) -> Optional[Tuple[str, Optional[str], int]]:
    if not prayers:
        log.error("No prayers available.")
        return None

    max_idx = max_index(prayers)
    idx = next_existing_index(current_index, prayers, max_idx)

    entry = prayers[str(idx)]
    name = entry.get("name")
    request = entry.get("request")

    log.info("Processing prayer %s: %s", idx, name)

    next_idx = idx + 1
    if next_idx > max_idx:
        next_idx = 1
    next_idx = next_existing_index(next_idx, prayers, max_idx)

    return name, request, next_idx

# ----------------------------
# Message builders
# ----------------------------
def build_plain_message(name: str, request: Optional[str], phone: Optional[str] = None) -> str:
    prayer_text = request or "למציאת עבודה טובה בקלות ובמהירות"
    msg = f"""שלום לכולן,

היום מתפללים על *{name}* – *{prayer_text}*.

ובנוסף – לרפואת הפצועים ולשמירה על החיילים.

🙏 בואו נעצור לרגע ונאמר פרק תהילים קצר.
"""
    if phone:
        msg += f"\n\n@{phone}"
    return msg

def build_html_message(name: str, request: Optional[str], phone: Optional[str] = None) -> str:
    prayer_text = request or "למציאת עבודה טובה בקלות ובמהירות"
    phone_tag = f"<br><br><strong>@{phone}</strong>" if phone else ""
    return f"""
    <html>
    <body>
      <div style="direction:rtl; text-align:right;">
        שלום לכולן,<br><br>
        היום מתפללים על <strong>{name}</strong> – <strong>{prayer_text}</strong>.<br>
        ובנוסף – לרפואת הפצועים ולשמירה על החיילים.<br><br>
        🙏 בואו נעצור לרגע ונאמר פרק תהילים קצר.<br>
        {phone_tag}
      </div>
    </body>
    </html>
    """

# ----------------------------
# Email
# ----------------------------
def send_email(
    name: str,
    request: Optional[str],
    recipient: str,
    prayer_id: str,
    target_list: str = "default",
) -> None:
    load_dotenv()
    sender = os.getenv("SENDER_EMAIL")
    password = os.getenv("SENDER_PASSWORD")

    if not sender or not password:
        log.error("Missing SENDER_EMAIL / SENDER_PASSWORD")
        return

    phone = None
    phones = load_prayers_with_phone(target_list)
    if prayer_id in phones:
        phone = phones[prayer_id].get("phone")

    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = "Today's Prayer Request"

    msg.attach(MIMEText(build_plain_message(name, request, phone), "plain"))
    msg.attach(MIMEText(build_html_message(name, request, phone), "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())

    log.info("Email sent to %s", recipient)

# ----------------------------
# CLI
# ----------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send next prayer")
    parser.add_argument("--input", type=str, default=None, help="Index or name")
    parser.add_argument("--email", type=str, default="rachelyayn@gmail.com")
    parser.add_argument("--state-file", type=str, default=str(Path.home() / "RunPrayers" / "last_index.txt"))
    parser.add_argument("--target-list", type=str, default="default")
    return parser.parse_args()

def main() -> None:
    args = parse_args()

    prayers = load_prayers(args.target_list)
    if not prayers:
        log.error("No prayers found.")
        return

    state_path = Path(args.state_file)
    start_idx = read_text_int(state_path, default=1)

    if args.input:
        try:
            start_idx = int(args.input)
        except ValueError:
            idx = find_index_by_name(args.input, prayers)
            if idx is None:
                raise ValueError(f"Name '{args.input}' not found")
            start_idx = idx

    result = process_next_prayer(start_idx, prayers)
    if not result:
        return

    name, request, next_idx = result
    write_text(state_path, str(next_idx))

    send_email(name, request, args.email, prayer_id=str(start_idx), target_list=args.target_list)

if __name__ == "__main__":
    main()

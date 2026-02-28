# settings.py
from dotenv import load_dotenv
import os
from pathlib import Path
from typing import Optional
import logging

# Load environment variables from .env file
load_dotenv()

log = logging.getLogger(__name__)

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    log.warning("DATABASE_URL not set, falling back to local mode")

# Email Configuration (Gmail SMTP)
EMAIL_USER = os.getenv("EMAIL_USER")          # Gmail address used to authenticate
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")  # Gmail App Password (not account password)
DEFAULT_RECIPIENT = os.getenv("DEFAULT_RECIPIENT", "recipient@example.com")

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Application Configuration
DATA_MODE = os.getenv("DATA_MODE", "database")  # 'local' or 'database'
API_KEY = os.getenv("API_KEY")  # Optional API authentication

# File Paths (cross-platform using pathlib)
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LAST_INDEX_FILE = DATA_DIR / "last_index.txt"
PRAYERS_DEFAULT_FILE = DATA_DIR / "prayers_default.json"
PRAYERS_WITH_PHONE_FILE = DATA_DIR / "prayers_with_phone_default.json"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Validation function
def validate_config() -> bool:
    """Validate required environment variables based on data mode."""
    missing = []
    
    if DATA_MODE == "database":
        if not SUPABASE_URL:
            missing.append("SUPABASE_URL")
        if not SUPABASE_KEY:
            missing.append("SUPABASE_KEY")
    
    if not EMAIL_USER:
        missing.append("EMAIL_USER")
    if not EMAIL_APP_PASSWORD:
        missing.append("EMAIL_APP_PASSWORD")
    
    if missing:
        log.error(f"Missing required environment variables: {', '.join(missing)}")
        return False
    
    return True

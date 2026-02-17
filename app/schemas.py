from pydantic import BaseModel
from typing import Optional

class PrayerIn(BaseModel):
    prayer_name: str
    request: Optional[str] = None
    phone: Optional[str] = None
    contact_name: Optional[str] = None
    tag_contact: bool = False
    target_list: str = "default"  # Added for compatibility with original API
    

"""
Prayer manager for handling CRUD operations and circular iteration logic.
Consolidated from prayer_logic/add_prayers.py, prayers_file.py, and prayer_utils.py.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Union
from ..settings import DATA_DIR, DATA_MODE, PRAYERS_DEFAULT_FILE, PRAYERS_WITH_PHONE_FILE, LAST_INDEX_FILE
from .supabase_client import get_supabase
from .email import send_email

log = logging.getLogger(__name__)

# Type aliases
PrayersDict = Dict[str, Dict]  # {"1": {"name":..., "request":...}}

class PrayerManager:
    """
    Unified prayer management with support for both local JSON and Supabase database.
    """
    
    def __init__(self, data_mode: str = None):
        self.data_mode = data_mode or DATA_MODE
        self.supabase = None
        
        if self.data_mode == "database":
            self.supabase = get_supabase()
            if not self.supabase or not self.supabase.is_connected():
                log.warning("Database mode requested but Supabase not available, falling back to local")
                self.data_mode = "local"
    
    # ===== Local File Operations =====
    
    def _get_prayers_file_path(self, target_list: str = "default") -> Path:
        """Get cross-platform path for prayers JSON file."""
        return DATA_DIR / f"prayers_{target_list}.json"
    
    def _get_phone_file_path(self, target_list: str = "default") -> Path:
        """Get cross-platform path for phones JSON file."""
        return DATA_DIR / f"prayers_with_phone_{target_list}.json"
    
    def _load_local_prayers(self, target_list: str = "default") -> Dict:
        """Load prayers from local JSON file."""
        path = self._get_prayers_file_path(target_list)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            log.error("Failed to load prayers from %s: %s", path, e)
            return {}
    
    def _save_local_prayers(self, data: Dict, target_list: str = "default") -> bool:
        """Save prayers to local JSON file."""
        path = self._get_prayers_file_path(target_list)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except Exception as e:
            log.error("Failed to save prayers to %s: %s", path, e)
            return False
    
    def _load_local_phones(self, target_list: str = "default") -> Dict:
        """Load phone data from local JSON file."""
        path = self._get_phone_file_path(target_list)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            log.error("Failed to load phones from %s: %s", path, e)
            return {}
    
    def _save_local_phones(self, data: Dict, target_list: str = "default") -> bool:
        """Save phone data to local JSON file."""
        path = self._get_phone_file_path(target_list)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except Exception as e:
            log.error("Failed to save phones to %s: %s", path, e)
            return False
    
    def _get_last_index(self) -> int:
        """Get last used index from file (local mode only)."""
        try:
            if LAST_INDEX_FILE.exists():
                return int(LAST_INDEX_FILE.read_text(encoding="utf-8").strip())
        except Exception as e:
            log.warning("Failed to read last index: %s", e)
        return 0
    
    def _save_last_index(self, index: int) -> bool:
        """Save last used index to file (local mode only)."""
        try:
            LAST_INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
            LAST_INDEX_FILE.write_text(str(index), encoding="utf-8")
            return True
        except Exception as e:
            log.error("Failed to save last index: %s", e)
            return False
    
    # ===== Prayer Entry Handling =====
    
    def _extract_prayer_data(self, entry: Union[Dict, list]) -> Tuple[Optional[str], Optional[str]]:
        """Extract name and request from prayer entry (handles both dict and list formats)."""
        if isinstance(entry, dict):
            return entry.get("name"), entry.get("request")
        elif isinstance(entry, list) and len(entry) >= 2:
            # List format: [name, request]
            return entry[0], entry[1]
        return None, None
    
    # ===== CRUD Operations =====
    
    def add_prayer(
        self,
        prayer_name: str,
        request: str = None,
        phone: str = None,
        contact_name: str = None,
        tag_contact: bool = False,
        target_list: str = "default"
    ) -> Optional[Union[str, int]]:
        """
        Add a new prayer to storage.
        
        Returns:
            str: Local mode returns string index
            int: Database mode returns integer ID
            None: On failure
        """
        if self.data_mode == "database" and self.supabase:
            # Database mode
            result = self.supabase.add_prayer(prayer_name, request, phone, contact_name, tag_contact)
            if result:
                log.info("Added prayer to database: %s (ID: %s)", prayer_name, result.get("id"))
                return result.get("id")
            return None
        
        else:
            # Local file mode
            prayers_dict = self._load_local_prayers(target_list)
            phones_dict = self._load_local_phones(target_list)
            
            # Determine next index safely
            if prayers_dict:
                max_index = max(int(k) for k in prayers_dict.keys())
                new_index = max_index + 1
            else:
                new_index = 1
            
            new_index_str = str(new_index)
            
            # Save prayer
            prayers_dict[new_index_str] = {
                "name": prayer_name,
                "request": request,
                "tag_contact": tag_contact
            }
            
            if not self._save_local_prayers(prayers_dict, target_list):
                return None
            
            # Save phone info (optional)
            if phone or contact_name:
                phones_dict[new_index_str] = {
                    "name": contact_name or prayer_name,
                    "phone": phone,
                    "tag": tag_contact
                }
                self._save_local_phones(phones_dict, target_list)
            
            log.info("Added prayer to local storage: %s (Index: %s)", prayer_name, new_index_str)
            return new_index_str
    
    def get_next_prayer(self, target_list: str = "default") -> Optional[Tuple[str, Optional[str], Optional[Union[str, int]]]]:
        """
        Get the next prayer using circular iteration logic.
        
        Returns:
            Tuple[name, request, id/index] or None if no prayers available
        """
        if self.data_mode == "database" and self.supabase:
            # Database mode with stateless circular logic
            record = self.supabase.get_next_prayer()
            if record:
                name, request, prayer_id = self.supabase.extract_prayer_data(record)
                return name, request, prayer_id
            return None
        
        else:
            # Local file mode with index-based circular logic
            prayers_dict = self._load_local_prayers(target_list)
            if not prayers_dict:
                log.error("No prayers available in local storage")
                return None
            
            current_index = self._get_last_index()
            max_idx = max(int(k) for k in prayers_dict.keys())
            
            # Find next valid index
            next_idx = current_index + 1
            if next_idx > max_idx:
                next_idx = 1
            
            # Ensure the index exists (handle gaps)
            for _ in range(max_idx):
                if str(next_idx) in prayers_dict:
                    break
                next_idx += 1
                if next_idx > max_idx:
                    next_idx = 1
            
            if str(next_idx) not in prayers_dict:
                log.error("No valid prayer index found")
                return None
            
            entry = prayers_dict[str(next_idx)]
            name, request = self._extract_prayer_data(entry)
            
            if name:
                # Update last index for next iteration
                self._save_last_index(next_idx)
                log.info("Selected prayer %s: %s", next_idx, name)
                return name, request, str(next_idx)
            
            return None
    
    def process_and_send_prayer(self, recipient: str = None, target_list: str = "default") -> bool:
        """
        Get next prayer and send via email.
        
        Returns:
            bool: True if successfully processed and sent, False otherwise
        """
        prayer_data = self.get_next_prayer(target_list)
        if not prayer_data:
            log.error("No prayer available to process")
            return False
        
        name, request, prayer_id = prayer_data
        
        # Mark as processing in database mode
        if self.data_mode == "database" and self.supabase and isinstance(prayer_id, int):
            if not self.supabase.set_processing(prayer_id):
                log.error("Failed to mark prayer %s as processing", prayer_id)
                return False
        
        # Send email
        success = send_email(name, request, recipient, prayer_id)
        
        # Update status based on email result
        if self.data_mode == "database" and self.supabase and isinstance(prayer_id, int):
            if success:
                self.supabase.mark_success(prayer_id)
            else:
                self.supabase.mark_failure(prayer_id, "Email sending failed")
        
        return success
    
    def get_prayer_count(self, target_list: str = "default") -> int:
        """Get total number of prayers."""
        if self.data_mode == "database" and self.supabase:
            # Would need a count endpoint for database mode
            log.warning("Prayer count not implemented for database mode")
            return 0
        else:
            prayers_dict = self._load_local_prayers(target_list)
            return len(prayers_dict)


# Global instance
prayer_manager: Optional[PrayerManager] = None

def get_prayer_manager(data_mode: str = None) -> PrayerManager:
    """Get global prayer manager instance, initializing if needed."""
    global prayer_manager
    if prayer_manager is None:
        prayer_manager = PrayerManager(data_mode)
    return prayer_manager
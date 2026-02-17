"""
Prayer storage interface and implementations.
Separated for better SOLID compliance and testability.
"""
import json
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Protocol
import logging
from ..settings import DATA_DIR, LAST_INDEX_FILE

log = logging.getLogger(__name__)

class PrayerData(Protocol):
    """Protocol defining prayer data structure."""
    name: str
    request: Optional[str]
    id: Union[str, int]

class PrayerStorageStrategy(ABC):
    """Abstract base class for prayer storage strategies."""
    
    @abstractmethod
    async def add_prayer(
        self,
        prayer_name: str,
        request: Optional[str] = None,
        phone: Optional[str] = None,
        contact_name: Optional[str] = None,
        tag_contact: bool = False,
        target_list: str = "default"
    ) -> Optional[Union[str, int]]:
        """Add a new prayer and return its ID/index."""
        pass
    
    @abstractmethod
    async def get_next_prayer(self, target_list: str = "default") -> Optional[Tuple[str, Optional[str], Union[str, int]]]:
        """Get next prayer using circular iteration."""
        pass
    
    @abstractmethod
    async def get_prayer_count(self, target_list: str = "default") -> int:
        """Get total prayer count."""
        pass


class LocalFileStorage(PrayerStorageStrategy):
    """Local JSON file storage implementation."""
    
    def __init__(self):
        self.lock = asyncio.Lock()
    
    async def _get_prayers_file_path(self, target_list: str) -> Path:
        """Get cross-platform path for prayers JSON file."""
        return DATA_DIR / f"prayers_{target_list}.json"
    
    async def _get_phone_file_path(self, target_list: str) -> Path:
        """Get cross-platform path for phones JSON file."""
        return DATA_DIR / f"prayers_with_phone_{target_list}.json"
    
    async def _load_json_file(self, path: Path) -> Dict:
        """Safely load JSON file."""
        try:
            if not path.exists():
                return {}
            content = await asyncio.get_event_loop().run_in_executor(
                None, path.read_text, "utf-8"
            )
            return json.loads(content)
        except Exception as e:
            log.error("Failed to load JSON from %s: %s", path, e)
            return {}
    
    async def _save_json_file(self, path: Path, data: Dict) -> bool:
        """Safely save JSON file."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            content = json.dumps(data, ensure_ascii=False, indent=2)
            await asyncio.get_event_loop().run_in_executor(
                None, path.write_text, content, "utf-8"
            )
            return True
        except Exception as e:
            log.error("Failed to save JSON to %s: %s", path, e)
            return False
    
    async def _get_last_index(self) -> int:
        """Get last used index."""
        try:
            if LAST_INDEX_FILE.exists():
                content = await asyncio.get_event_loop().run_in_executor(
                    None, LAST_INDEX_FILE.read_text, "utf-8"
                )
                return int(content.strip())
        except Exception as e:
            log.warning("Failed to read last index: %s", e)
        return 0
    
    async def _save_last_index(self, index: int) -> bool:
        """Save last used index."""
        try:
            LAST_INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.get_event_loop().run_in_executor(
                None, LAST_INDEX_FILE.write_text, str(index), "utf-8"
            )
            return True
        except Exception as e:
            log.error("Failed to save last index: %s", e)
            return False
    
    def _extract_prayer_data(self, entry: Union[Dict, list]) -> Tuple[Optional[str], Optional[str]]:
        """Extract name and request from prayer entry."""
        if isinstance(entry, dict):
            return entry.get("name"), entry.get("request")
        elif isinstance(entry, list) and len(entry) >= 2:
            return entry[0], entry[1]
        return None, None
    
    async def add_prayer(
        self,
        prayer_name: str,
        request: Optional[str] = None,
        phone: Optional[str] = None,
        contact_name: Optional[str] = None,
        tag_contact: bool = False,
        target_list: str = "default"
    ) -> Optional[str]:
        """Add prayer to local JSON storage."""
        async with self.lock:
            prayers_path = await self._get_prayers_file_path(target_list)
            phones_path = await self._get_phone_file_path(target_list)
            
            prayers_dict = await self._load_json_file(prayers_path)
            phones_dict = await self._load_json_file(phones_path)
            
            # Determine next index
            new_index = 1
            if prayers_dict:
                max_index = max(int(k) for k in prayers_dict.keys())
                new_index = max_index + 1
            
            new_index_str = str(new_index)
            
            # Save prayer
            prayers_dict[new_index_str] = {
                "name": prayer_name,
                "request": request,
                "tag_contact": tag_contact
            }
            
            if not await self._save_json_file(prayers_path, prayers_dict):
                return None
            
            # Save phone info if provided
            if phone or contact_name:
                phones_dict[new_index_str] = {
                    "name": contact_name or prayer_name,
                    "phone": phone,
                    "tag": tag_contact
                }
                await self._save_json_file(phones_path, phones_dict)
            
            log.info("Added prayer to local storage: %s (Index: %s)", prayer_name, new_index_str)
            return new_index_str
    
    async def get_next_prayer(self, target_list: str = "default") -> Optional[Tuple[str, Optional[str], str]]:
        """Get next prayer using circular iteration."""
        prayers_path = await self._get_prayers_file_path(target_list)
        prayers_dict = await self._load_json_file(prayers_path)
        
        if not prayers_dict:
            log.error("No prayers available in local storage")
            return None
        
        current_index = await self._get_last_index()
        max_idx = max(int(k) for k in prayers_dict.keys())
        
        # Find next valid index
        next_idx = current_index + 1
        if next_idx > max_idx:
            next_idx = 1
        
        # Handle gaps in indices
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
            await self._save_last_index(next_idx)
            log.info("Selected prayer %s: %s", next_idx, name)
            return name, request, str(next_idx)
        
        return None
    
    async def get_prayer_count(self, target_list: str = "default") -> int:
        """Get total prayer count."""
        prayers_path = await self._get_prayers_file_path(target_list)
        prayers_dict = await self._load_json_file(prayers_path)
        return len(prayers_dict)


class DatabaseStorage(PrayerStorageStrategy):
    """Database storage implementation using async Supabase client."""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    async def add_prayer(
        self,
        prayer_name: str,
        request: Optional[str] = None,
        phone: Optional[str] = None,
        contact_name: Optional[str] = None,
        tag_contact: bool = False,
        target_list: str = "default"
    ) -> Optional[int]:
        """Add prayer to database."""
        if not self.supabase or not await self.supabase.is_connected():
            log.error("Database not available for prayer addition")
            return None
        
        result = await self.supabase.add_prayer(prayer_name, request, phone, contact_name, tag_contact)
        if result:
            prayer_id = result.get("id")
            log.info("Added prayer to database: %s (ID: %s)", prayer_name, prayer_id)
            return prayer_id
        return None
    
    async def get_next_prayer(self, target_list: str = "default") -> Optional[Tuple[str, Optional[str], int]]:
        """Get next prayer from database using circular logic."""
        if not self.supabase or not await self.supabase.is_connected():
            log.error("Database not available for prayer retrieval")
            return None
        
        record = await self.supabase.get_next_prayer()
        if record:
            name, request, prayer_id = self.supabase.extract_prayer_data(record)
            if name and prayer_id:
                return name, request, prayer_id
        return None
    
    async def get_prayer_count(self, target_list: str = "default") -> int:
        """Get prayer count from database."""
        # Would need to implement count endpoint
        log.warning("Prayer count not implemented for database mode")
        return 0
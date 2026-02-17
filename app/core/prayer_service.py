"""
Refactored prayer manager using dependency injection and SOLID principles.
Replaces the monolithic prayer_manager.py with clean architecture.
"""
import logging
from typing import Optional, Tuple, Union, Dict, Any
from .storage_strategies import PrayerStorageStrategy, LocalFileStorage, DatabaseStorage
from .email import send_email
from .supabase_client import get_supabase
from ..settings import DATA_MODE

log = logging.getLogger(__name__)

class PrayerService:
    """
    Main prayer service using dependency injection and strategy pattern.
    Follows single responsibility principle - coordinates between storage and email.
    """
    
    def __init__(self, storage_strategy: PrayerStorageStrategy, email_service=None):
        self.storage = storage_strategy
        self.email_service = email_service or send_email
        log.info("PrayerService initialized with %s storage", type(storage_strategy).__name__)
    
    async def add_prayer(
        self,
        prayer_name: str,
        request: Optional[str] = None,
        phone: Optional[str] = None,
        contact_name: Optional[str] = None,
        tag_contact: bool = False,
        target_list: str = "default"
    ) -> Optional[Union[str, int]]:
        """Add a new prayer using the configured storage strategy."""
        if not prayer_name or not prayer_name.strip():
            log.error("Prayer name cannot be empty")
            return None
        
        try:
            result = await self.storage.add_prayer(
                prayer_name.strip(),
                request.strip() if request else None,
                phone.strip() if phone else None,
                contact_name.strip() if contact_name else None,
                tag_contact,
                target_list
            )
            
            if result:
                log.info("Successfully added prayer: %s", prayer_name)
                return result
            else:
                log.error("Failed to add prayer: %s", prayer_name)
                return None
                
        except Exception as e:
            log.error("Error adding prayer %s: %s", prayer_name, e, exc_info=True)
            return None
    
    async def get_next_prayer(self, target_list: str = "default") -> Optional[Tuple[str, Optional[str], Union[str, int]]]:
        """Get the next prayer using circular iteration."""
        try:
            return await self.storage.get_next_prayer(target_list)
        except Exception as e:
            log.error("Error getting next prayer: %s", e, exc_info=True)
            return None
    
    async def process_and_send_prayer(
        self, 
        recipient: Optional[str] = None, 
        target_list: str = "default",
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Get next prayer and send via email with comprehensive result tracking.
        
        Returns:
            Dict with success status, prayer info, and detailed results
        """
        result = {
            "success": False,
            "prayer": None,
            "email_sent": False,
            "error": None,
            "storage_updated": False
        }
        
        try:
            # Get next prayer
            prayer_data = await self.get_next_prayer(target_list)
            if not prayer_data:
                result["error"] = "No prayer available"
                return result
            
            name, request, prayer_id = prayer_data
            result["prayer"] = {
                "name": name,
                "request": request,
                "id": prayer_id
            }
            
            # Mark as processing if database mode
            if hasattr(self.storage, 'supabase') and isinstance(prayer_id, int):
                processing_success = await self.storage.supabase.set_processing(prayer_id)
                if not processing_success:
                    result["error"] = "Failed to mark prayer as processing"
                    return result
            
            # Send email
            email_success = await self.email_service(name, request, recipient, prayer_id, max_retries)
            result["email_sent"] = email_success
            
            # Update storage based on email result
            if hasattr(self.storage, 'supabase') and isinstance(prayer_id, int):
                if email_success:
                    storage_success = await self.storage.supabase.mark_success(prayer_id)
                else:
                    storage_success = await self.storage.supabase.mark_failure(prayer_id, "Email sending failed")
                result["storage_updated"] = storage_success
            
            result["success"] = email_success
            
            if email_success:
                log.info("Successfully processed and sent prayer: %s (ID: %s)", name, prayer_id)
            else:
                log.error("Failed to send email for prayer: %s (ID: %s)", name, prayer_id)
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing prayer: {e}"
            log.error(error_msg, exc_info=True)
            result["error"] = error_msg
            return result
    
    async def get_prayer_count(self, target_list: str = "default") -> int:
        """Get total prayer count."""
        try:
            return await self.storage.get_prayer_count(target_list)
        except Exception as e:
            log.error("Error getting prayer count: %s", e)
            return 0
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive service status."""
        try:
            status = {
                "storage_type": type(self.storage).__name__,
                "storage_healthy": True,
                "email_service_available": callable(self.email_service),
                "prayer_count": 0
            }
            
            # Test storage health
            try:
                status["prayer_count"] = await self.storage.get_prayer_count()
            except Exception as e:
                status["storage_healthy"] = False
                status["storage_error"] = str(e)
            
            # Test database connectivity if applicable
            if hasattr(self.storage, 'supabase'):
                status["database_connected"] = await self.storage.supabase.is_connected()
            
            return status
            
        except Exception as e:
            return {
                "storage_type": "unknown",
                "storage_healthy": False,
                "error": str(e)
            }


class PrayerServiceFactory:
    """Factory for creating prayer services with appropriate storage strategies."""
    
    @staticmethod
    async def create_service(data_mode: Optional[str] = None) -> PrayerService:
        """Create prayer service with appropriate storage strategy."""
        mode = data_mode or DATA_MODE
        
        if mode == "database":
            try:
                supabase_client = await get_supabase()
                if supabase_client and await supabase_client.is_connected():
                    storage = DatabaseStorage(supabase_client)
                    log.info("Created PrayerService with database storage")
                    return PrayerService(storage)
                else:
                    log.warning("Database requested but not available, falling back to local storage")
                    mode = "local"
            except Exception as e:
                log.error("Failed to initialize database storage: %s", e)
                mode = "local"
        
        if mode == "local":
            storage = LocalFileStorage()
            log.info("Created PrayerService with local file storage")
            return PrayerService(storage)
        
        raise ValueError(f"Unsupported data mode: {mode}")


# Global service instance with lazy initialization
_prayer_service: Optional[PrayerService] = None

async def get_prayer_service(data_mode: Optional[str] = None) -> PrayerService:
    """Get global prayer service instance, creating if needed."""
    global _prayer_service
    
    if _prayer_service is None:
        _prayer_service = await PrayerServiceFactory.create_service(data_mode)
    
    return _prayer_service

async def reset_prayer_service():
    """Reset global service instance (useful for testing)."""
    global _prayer_service
    _prayer_service = None
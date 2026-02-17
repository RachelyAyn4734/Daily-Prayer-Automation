"""
Async Supabase client for prayer database management.
Migrated from prayer_logic/supabase_client.py with enhanced security, async operations, and connection pooling.
"""
import asyncio
from datetime import datetime
from typing import Dict, Optional, Tuple
import logging
import aiohttp
import json
from ..settings import SUPABASE_URL, SUPABASE_KEY

log = logging.getLogger(__name__)

class AsyncSupabaseManager:
    """Enhanced async Supabase client with connection pooling and stateless circular iteration logic."""
    
    def __init__(self, max_connections: int = 10):
        self.url = SUPABASE_URL
        self.key = SUPABASE_KEY
        self.base_url = f"{self.url}/rest/v1" if self.url else None
        self.headers = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.max_connections = max_connections
        self._initialized = False
        
        if not self.url or not self.key:
            log.error("Missing SUPABASE_URL or SUPABASE_KEY in environment")
            return
        
        self.headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "apikey": self.key
        }
    
    async def _ensure_session(self):
        """Ensure aiohttp session is initialized with connection pooling."""
        if not self.session or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=self.max_connections,
                limit_per_host=self.max_connections,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.headers,
                raise_for_status=False
            )
        
        if not self._initialized:
            await self._test_connection()
            self._initialized = True
    
    async def _test_connection(self):
        """Test connection to Supabase."""
        if not self.base_url or not self.session:
            raise ConnectionError("Supabase client not properly initialized")
        
        try:
            async with self.session.get(f"{self.base_url}/prayers?limit=1") as response:
                if response.status >= 400:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status
                    )
                log.info("Supabase connection test successful")
        except Exception as e:
            log.error("Supabase connection test failed: %s", e)
            raise
    
    async def is_connected(self) -> bool:
        """Check if client is connected and ready."""
        try:
            await self._ensure_session()
            return self._initialized
        except Exception:
            return False
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_next_prayer(self) -> Optional[Dict]:
        """
        Fetch the next prayer using circular wrap logic based on last_used_at.
        
        Strategy for stateless circular iteration:
        1. Find the record with the most recent last_used_at (or NULL if none processed)
        2. Query for records with id > that record's id, ordered by id ASC
        3. If no results, wrap around to the record with lowest id
        
        This ensures deterministic iteration even across server restarts.
        """
        await self._ensure_session()
        
        try:
            # Step 1: Find the most recently used prayer
            async with self.session.get(
                f"{self.base_url}/prayers?select=id,last_used_at&order=last_used_at.desc.nullslast&limit=1"
            ) as response:
                response.raise_for_status()
                last_used_data = await response.json()
            
            last_id = None
            if last_used_data and len(last_used_data) > 0:
                last_id = last_used_data[0]["id"]
            
            # Step 2: Forward scan - find next id after last_used
            if last_id is not None:
                async with self.session.get(
                    f"{self.base_url}/prayers?id=gt.{last_id}&order=id.asc&limit=1"
                ) as response:
                    response.raise_for_status()
                    next_data = await response.json()
                    
                    if next_data and len(next_data) > 0:
                        return next_data[0]
            
            # Step 3: Wrap around - fetch lowest id prayer
            async with self.session.get(
                f"{self.base_url}/prayers?order=id.asc&limit=1"
            ) as response:
                response.raise_for_status()
                first_data = await response.json()
                
                if first_data and len(first_data) > 0:
                    return first_data[0]
            
            log.warning("No prayers available in database")
            return None
        
        except Exception as e:
            log.error("Failed to fetch next prayer: %s", e, exc_info=True)
            return None
    
    async def get_prayer_by_id(self, prayer_id: int) -> Optional[Dict]:
        """Fetch a specific prayer by ID."""
        await self._ensure_session()
        
        try:
            async with self.session.get(
                f"{self.base_url}/prayers?id=eq.{prayer_id}"
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                if data and len(data) > 0:
                    return data[0]
                return None
        except Exception as e:
            log.error("Failed to fetch prayer by ID %s: %s", prayer_id, e)
            return None
    
    async def add_prayer(self, prayer_name: str, request: str = None, phone: str = None, contact_name: str = None, tag_contact: bool = False) -> Optional[Dict]:
        """Add a new prayer to the database."""
        await self._ensure_session()
            
        try:
            payload = {
                "prayer_name": prayer_name,
                "request": request,
                "phone": phone,
                "contact_name": contact_name,
                "tag_contact": tag_contact,
                "status": "pending"
            }
            
            async with self.session.post(
                f"{self.base_url}/prayers",
                json=payload
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                if data and len(data) > 0:
                    log.info("Added prayer: %s", prayer_name)
                    return data[0]
                return None
        except Exception as e:
            log.error("Failed to add prayer %s: %s", prayer_name, e)
            return None
    
    async def set_processing(self, prayer_id: int) -> bool:
        """Atomically set prayer status to 'processing' to prevent race conditions."""
        await self._ensure_session()
            
        try:
            payload = {"status": "processing"}
            async with self.session.patch(
                f"{self.base_url}/prayers?id=eq.{prayer_id}",
                json=payload
            ) as response:
                response.raise_for_status()
                return True
        except Exception as e:
            log.error("Failed to set processing status for prayer %s: %s", prayer_id, e)
            return False
    
    async def mark_success(self, prayer_id: int) -> bool:
        """Mark prayer as completed and update last_used_at timestamp."""
        await self._ensure_session()
            
        try:
            payload = {
                "status": "completed",
                "last_used_at": datetime.now().isoformat(),
                "last_error": None
            }
            async with self.session.patch(
                f"{self.base_url}/prayers?id=eq.{prayer_id}",
                json=payload
            ) as response:
                response.raise_for_status()
                return True
        except Exception as e:
            log.error("Failed to mark prayer %s as success: %s", prayer_id, e)
            return False
    
    async def mark_failure(self, prayer_id: int, error_msg: str) -> bool:
        """
        Mark prayer as failed without updating last_used_at.
        This keeps failed records high-priority for the next run.
        """
        await self._ensure_session()
            
        try:
            payload = {
                "status": "failed",
                "last_error": error_msg
            }
            async with self.session.patch(
                f"{self.base_url}/prayers?id=eq.{prayer_id}",
                json=payload
            ) as response:
                response.raise_for_status()
                return True
        except Exception as e:
            log.error("Failed to mark prayer %s as failure: %s", prayer_id, e)
            return False
    
    def extract_prayer_data(self, record: Dict) -> Tuple[str, Optional[str], Optional[int]]:
        """Extract prayer name, request, and id from database record."""
        name = record.get("prayer_name")
        request = record.get("request")
        prayer_id = record.get("id")
        return name, request, prayer_id


# Global instance
supabase_manager: Optional[AsyncSupabaseManager] = None

async def init_supabase(max_connections: int = 10) -> AsyncSupabaseManager:
    """Initialize global async Supabase manager instance."""
    global supabase_manager
    supabase_manager = AsyncSupabaseManager(max_connections)
    await supabase_manager._ensure_session()  # Initialize connection pool
    return supabase_manager

async def get_supabase() -> Optional[AsyncSupabaseManager]:
    """Get global async Supabase manager instance, initializing if needed."""
    global supabase_manager
    if supabase_manager is None:
        await init_supabase()
    return supabase_manager

async def cleanup_supabase():
    """Clean up global Supabase manager connections."""
    global supabase_manager
    if supabase_manager:
        await supabase_manager.close()
        supabase_manager = None
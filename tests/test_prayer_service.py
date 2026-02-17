"""
Basic test configuration and sample tests for the enhanced prayer service.
"""
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock
import sys
from pathlib import Path

# Add the app directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

@pytest_asyncio.fixture
async def mock_supabase():
    """Mock Supabase client for testing."""
    mock = AsyncMock()
    mock.is_connected.return_value = True
    mock.add_prayer.return_value = {"id": 123}
    mock.get_next_prayer.return_value = {
        "id": 1,
        "prayer_name": "Test Prayer",
        "request": "Test request"
    }
    mock.extract_prayer_data.return_value = ("Test Prayer", "Test request", 1)
    return mock

@pytest_asyncio.fixture
async def mock_email_service():
    """Mock email service for testing."""
    mock = AsyncMock()
    mock.return_value = True  # Simulate successful email sending
    return mock

class TestPrayerService:
    """Test cases for the prayer service."""
    
    @pytest_asyncio.async_test
    async def test_add_prayer_success(self, mock_supabase, mock_email_service):
        """Test successful prayer addition."""
        from core.storage_strategies import DatabaseStorage
        from core.prayer_service import PrayerService
        
        storage = DatabaseStorage(mock_supabase)
        service = PrayerService(storage, mock_email_service)
        
        result = await service.add_prayer("Test Prayer", "Test request")
        
        assert result == 123
        mock_supabase.add_prayer.assert_called_once()
    
    @pytest_asyncio.async_test 
    async def test_get_next_prayer(self, mock_supabase, mock_email_service):
        """Test getting next prayer."""
        from core.storage_strategies import DatabaseStorage
        from core.prayer_service import PrayerService
        
        storage = DatabaseStorage(mock_supabase)
        service = PrayerService(storage, mock_email_service)
        
        result = await service.get_next_prayer()
        
        assert result == ("Test Prayer", "Test request", 1)
        mock_supabase.get_next_prayer.assert_called_once()
    
    @pytest_asyncio.async_test
    async def test_process_and_send_prayer(self, mock_supabase, mock_email_service):
        """Test complete prayer processing and sending."""
        from core.storage_strategies import DatabaseStorage
        from core.prayer_service import PrayerService
        
        storage = DatabaseStorage(mock_supabase)
        service = PrayerService(storage, mock_email_service)
        
        result = await service.process_and_send_prayer()
        
        assert result["success"] is True
        assert result["email_sent"] is True
        assert result["prayer"]["name"] == "Test Prayer"
        
        mock_supabase.get_next_prayer.assert_called_once()
        mock_email_service.assert_called_once()

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
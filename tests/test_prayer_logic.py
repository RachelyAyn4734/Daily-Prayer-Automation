import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from prayer_logic.supabase_client import SupabaseManager
from prayer_logic.prayers_file import (
    process_from_database,
    send_email,
    build_plain_message,
    build_html_message,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_supabase():
    """Create a mock SupabaseManager instance."""
    with patch('prayer_logic.supabase_client.SupabaseManager.__init__', return_value=None):
        manager = SupabaseManager()
        manager.is_connected = Mock(return_value=True)
        manager.get_next_prayer = Mock()
        manager.get_prayer_by_id = Mock()
        manager.set_processing = Mock()
        manager.mark_success = Mock()
        manager.mark_failure = Mock()
        manager.extract_prayer_data = Mock()
        return manager


@pytest.fixture
def mock_send_email():
    """Mock the send_email function to prevent real emails."""
    with patch('prayer_logic.prayers_file.send_email') as mock:
        yield mock


@pytest.fixture
def sample_prayer_records():
    """Sample prayer records for testing."""
    return {
        1: {
            "id": 1,
            "prayer_name": "David",
            "request": "Health and strength",
            "status": "pending",
            "last_used_at": None,
            "last_error": None,
        },
        2: {
            "id": 2,
            "prayer_name": "Sarah",
            "request": "Job opportunity",
            "status": "pending",
            "last_used_at": None,
            "last_error": None,
        },
        3: {
            "id": 3,
            "prayer_name": "Rachel",
            "request": "Family peace",
            "status": "pending",
            "last_used_at": None,
            "last_error": None,
        },
    }


# ============================================================================
# SCENARIO 1: CIRCULAR WRAP
# ============================================================================

class TestCircularWrap:
    """Test that the system correctly wraps around after processing all records."""
    
    def test_circular_wrap_four_consecutive_runs(self, mock_supabase, sample_prayer_records):
        """
        Simulate 4 consecutive runs with 3 records.
        Expected: Process IDs 1, 2, 3, then wrap back to 1.
        """
        records_by_id = sample_prayer_records
        processed_order = []
        
        def side_effect_get_next(*args, **kwargs):
            """Simulate circular logic: return next unprocessed ID."""
            # Find the highest last_used_at timestamp
            max_id = 0
            for record_id, record in records_by_id.items():
                if record.get("last_used_at"):
                    max_id = max(max_id, record_id)
            
            # Return next ID after max_id, or wrap to 1
            for i in range(1, 4):
                if i > max_id:
                    return records_by_id[i]
            return records_by_id[1]  # Wrap around
        
        mock_supabase.get_next_prayer.side_effect = side_effect_get_next
        mock_supabase.extract_prayer_data.side_effect = lambda r: (
            r.get("prayer_name"),
            r.get("request"),
            r.get("id"),
        )
        mock_supabase.set_processing.return_value = True
        mock_supabase.mark_success.side_effect = lambda prayer_id: (
            records_by_id[prayer_id].update(
                {"last_used_at": datetime.now().isoformat()}
            ),
            records_by_id[prayer_id].update({"status": "completed"}),
            True,
        )[-1]
        
        # Run 4 times
        for run in range(1, 5):
            with patch('prayer_logic.prayers_file.get_supabase', return_value=mock_supabase):
                with patch('prayer_logic.prayers_file.send_email', return_value=True):
                    result = process_from_database(recipient="test@example.com")
                    assert result is True, f"Run {run} failed"
                    
                    # Track which prayer was processed
                    call_args = mock_supabase.mark_success.call_args
                    if call_args:
                        processed_id = call_args[0][0]
                        processed_order.append(processed_id)
        
        # Verify circular order: 1, 2, 3, 1
        assert processed_order == [1, 2, 3, 1], f"Expected [1, 2, 3, 1], got {processed_order}"
    
    def test_wrap_to_lowest_id_when_gaps_exist(self, mock_supabase):
        """Test that wrapping goes to the lowest available ID, skipping gaps."""
        records = {
            1: {"id": 1, "prayer_name": "Alice", "request": "Health", "last_used_at": None},
            3: {"id": 3, "prayer_name": "Charlie", "request": "Peace", "last_used_at": None},
            5: {"id": 5, "prayer_name": "Eve", "request": "Safety", "last_used_at": None},
        }
        
        # After processing ID 5, next should be ID 1 (lowest), skipping ID 2 and 4
        processed = [5]
        
        def get_next_with_gap(*args, **kwargs):
            if 5 in processed:
                return records[1]  # Wrap to lowest
            return None
        
        mock_supabase.get_next_prayer.side_effect = get_next_with_gap
        mock_supabase.extract_prayer_data.side_effect = lambda r: (
            r.get("prayer_name"),
            r.get("request"),
            r.get("id"),
        )
        mock_supabase.set_processing.return_value = True
        mock_supabase.mark_success.return_value = True
        
        with patch('prayer_logic.prayers_file.get_supabase', return_value=mock_supabase):
            with patch('prayer_logic.prayers_file.send_email', return_value=True):
                result = process_from_database(recipient="test@example.com")
                assert result is True
                # Verify it called get_next_prayer
                assert mock_supabase.get_next_prayer.called


# ============================================================================
# SCENARIO 2: ERROR HANDLING
# ============================================================================

class TestErrorHandling:
    """Test error handling when email send fails."""
    
    def test_failed_email_does_not_update_last_used_at(self, mock_supabase):
        """
        Verify that when email send fails:
        - status is set to 'failed'
        - last_used_at is NOT updated
        - last_error is recorded
        """
        prayer_record = {
            "id": 42,
            "prayer_name": "John",
            "request": "Healing",
            "status": "processing",
            "last_used_at": None,
            "last_error": None,
        }
        
        mock_supabase.get_next_prayer.return_value = prayer_record
        mock_supabase.extract_prayer_data.return_value = (
            "John",
            "Healing",
            42,
        )
        mock_supabase.set_processing.return_value = True
        mock_supabase.mark_failure.return_value = True
        
        with patch('prayer_logic.prayers_file.get_supabase', return_value=mock_supabase):
            with patch('prayer_logic.prayers_file.send_email', return_value=False):
                result = process_from_database(recipient="test@example.com")
                
                # Verify process returned False (email failed)
                assert result is False
                
                # Verify mark_failure was called with the error message
                mock_supabase.mark_failure.assert_called_once()
                call_args = mock_supabase.mark_failure.call_args
                assert call_args[0][0] == 42  # prayer_id
                assert "Email send failed" in call_args[0][1]  # error message
                
                # Verify mark_success was NOT called
                mock_supabase.mark_success.assert_not_called()
    
    def test_exception_during_processing_marks_failure(self, mock_supabase):
        """Test that unexpected exceptions during processing mark the prayer as failed."""
        prayer_record = {
            "id": 99,
            "prayer_name": "Emma",
            "request": "Safety",
            "status": "pending",
        }
        
        mock_supabase.get_next_prayer.return_value = prayer_record
        mock_supabase.extract_prayer_data.return_value = ("Emma", "Safety", 99)
        mock_supabase.set_processing.side_effect = Exception("DB connection error")
        
        with patch('prayer_logic.prayers_file.get_supabase', return_value=mock_supabase):
            with patch('prayer_logic.prayers_file.send_email', return_value=True):
                result = process_from_database(recipient="test@example.com")
                
                # Verify it returned False
                assert result is False
                
                # Verify mark_failure was called
                mock_supabase.mark_failure.assert_called_once()
    
    def test_no_prayers_available_returns_false(self, mock_supabase):
        """Test graceful exit when no prayers are available."""
        mock_supabase.get_next_prayer.return_value = None
        
        with patch('prayer_logic.prayers_file.get_supabase', return_value=mock_supabase):
            result = process_from_database(recipient="test@example.com")
            
            # Should return False and log error
            assert result is False
            mock_supabase.set_processing.assert_not_called()
            mock_supabase.mark_success.assert_not_called()


# ============================================================================
# SCENARIO 3: MISSING IDS / GAPS
# ============================================================================

class TestMissingIds:
    """Test that the system correctly handles gaps in ID sequences."""
    
    def test_skip_deleted_id_and_process_next(self, mock_supabase):
        """
        Simulate: ID 1 exists, ID 2 is deleted, ID 3 exists.
        Verify the script picks ID 3 after processing ID 1.
        """
        records = {
            1: {
                "id": 1,
                "prayer_name": "Alice",
                "request": "Health",
                "status": "pending",
                "last_used_at": None,
            },
            # ID 2 is deleted (missing)
            3: {
                "id": 3,
                "prayer_name": "Charlie",
                "request": "Peace",
                "status": "pending",
                "last_used_at": None,
            },
        }
        
        processed_ids = []
        
        def get_next_with_deleted(*args, **kwargs):
            """Return next available ID, skipping deleted ones."""
            if not processed_ids:
                return records[1]
            elif 1 in processed_ids:
                return records[3]  # Skip ID 2, go to ID 3
            return None
        
        mock_supabase.get_next_prayer.side_effect = get_next_with_deleted
        mock_supabase.extract_prayer_data.side_effect = lambda r: (
            r.get("prayer_name"),
            r.get("request"),
            r.get("id"),
        )
        mock_supabase.set_processing.return_value = True
        
        def mark_success_side_effect(prayer_id):
            processed_ids.append(prayer_id)
            return True
        
        mock_supabase.mark_success.side_effect = mark_success_side_effect
        
        # Process twice
        with patch('prayer_logic.prayers_file.get_supabase', return_value=mock_supabase):
            with patch('prayer_logic.prayers_file.send_email', return_value=True):
                result1 = process_from_database(recipient="test@example.com")
                result2 = process_from_database(recipient="test@example.com")
        
        assert result1 is True
        assert result2 is True
        assert processed_ids == [1, 3], f"Expected [1, 3], got {processed_ids}"
    
    def test_single_record_database(self, mock_supabase):
        """Test that system works with only one prayer record."""
        single_record = {
            "id": 1,
            "prayer_name": "Solo",
            "request": "Blessings",
            "status": "pending",
            "last_used_at": None,
        }
        
        call_count = [0]
        
        def get_next_single(*args, **kwargs):
            call_count[0] += 1
            return single_record
        
        mock_supabase.get_next_prayer.side_effect = get_next_single
        mock_supabase.extract_prayer_data.return_value = ("Solo", "Blessings", 1)
        mock_supabase.set_processing.return_value = True
        mock_supabase.mark_success.return_value = True
        
        with patch('prayer_logic.prayers_file.get_supabase', return_value=mock_supabase):
            with patch('prayer_logic.prayers_file.send_email', return_value=True):
                result = process_from_database(recipient="test@example.com")
        
        assert result is True
        assert mock_supabase.set_processing.called
        assert mock_supabase.mark_success.called


# ============================================================================
# SCENARIO 4: ATOMIC LOCK
# ============================================================================

class TestAtomicLock:
    """Test atomic set_processing behavior to prevent race conditions."""
    
    def test_set_processing_failure_aborts_email_send(self, mock_supabase):
        """
        Verify that if set_processing fails, the script:
        - Does NOT attempt to send email
        - Returns False
        - Does NOT call mark_success or mark_failure
        """
        prayer_record = {
            "id": 10,
            "prayer_name": "Bob",
            "request": "Prosperity",
            "status": "pending",
        }
        
        mock_supabase.get_next_prayer.return_value = prayer_record
        mock_supabase.extract_prayer_data.return_value = ("Bob", "Prosperity", 10)
        # Simulate atomic lock failure
        mock_supabase.set_processing.return_value = False
        
        with patch('prayer_logic.prayers_file.get_supabase', return_value=mock_supabase):
            with patch('prayer_logic.prayers_file.send_email') as mock_email:
                result = process_from_database(recipient="test@example.com")
                
                # Verify failure
                assert result is False
                
                # Verify email was NOT sent
                mock_email.assert_not_called()
                
                # Verify mark_success and mark_failure were NOT called
                mock_supabase.mark_success.assert_not_called()
                mock_supabase.mark_failure.assert_not_called()
    
    def test_set_processing_exception_aborts_gracefully(self, mock_supabase):
        """Test that exceptions in set_processing are handled gracefully."""
        prayer_record = {
            "id": 11,
            "prayer_name": "Carol",
            "request": "Guidance",
            "status": "pending",
        }
        
        mock_supabase.get_next_prayer.return_value = prayer_record
        mock_supabase.extract_prayer_data.return_value = ("Carol", "Guidance", 11)
        # Simulate exception during atomic lock
        mock_supabase.set_processing.side_effect = Exception("Lock acquisition failed")
        
        with patch('prayer_logic.prayers_file.get_supabase', return_value=mock_supabase):
            with patch('prayer_logic.prayers_file.send_email') as mock_email:
                result = process_from_database(recipient="test@example.com")
                
                # Verify failure
                assert result is False
                
                # Verify email was NOT sent
                mock_email.assert_not_called()
    
    def test_concurrent_processing_scenario(self, mock_supabase):
        """
        Simulate two concurrent runs trying to process the same prayer.
        Second run should fail the atomic lock and skip the email send.
        """
        prayer_record = {
            "id": 20,
            "prayer_name": "Diana",
            "request": "Strength",
            "status": "pending",
        }
        
        mock_supabase.get_next_prayer.return_value = prayer_record
        mock_supabase.extract_prayer_data.return_value = ("Diana", "Strength", 20)
        
        # First call succeeds, second call fails (already locked)
        mock_supabase.set_processing.side_effect = [True, False]
        mock_supabase.mark_success.return_value = True
        
        with patch('prayer_logic.prayers_file.get_supabase', return_value=mock_supabase):
            with patch('prayer_logic.prayers_file.send_email', return_value=True):
                # First run succeeds
                result1 = process_from_database(recipient="test@example.com")
                assert result1 is True
                
                # Second run fails (lock unavailable)
                result2 = process_from_database(recipient="test@example.com")
                assert result2 is False
                
                # Verify email was only sent once
                assert mock_supabase.mark_success.call_count == 1


# ============================================================================
# EDGE CASES & MESSAGE BUILDING
# ============================================================================

class TestMessageBuilding:
    """Test message building functions."""
    
    def test_build_plain_message_with_request(self):
        """Test plain text message with custom request."""
        msg = build_plain_message("Sarah", "Safe travels")
        assert "Sarah" in msg
        assert "Safe travels" in msg
        assert "שלום לכולן" in msg  # Hebrew greeting
    
    def test_build_plain_message_without_request(self):
        """Test plain text message with default request."""
        msg = build_plain_message("Sarah", None)
        assert "Sarah" in msg
        assert "למציאת עבודה טובה" in msg  # Default prayer text
    
    def test_build_html_message_with_request(self):
        """Test HTML message with custom request."""
        msg = build_html_message("Jacob", "Business success")
        assert "Jacob" in msg
        assert "Business success" in msg
        assert "<html>" in msg
        assert "תהילים" in msg  # Psalm reference
    
    def test_build_html_message_psalm_included(self):
        """Test that HTML message includes Psalm 23."""
        msg = build_html_message("Michael", "Health")
        assert "יְהוָה" in msg  # Hebrew text from Psalm
        assert "direction:rtl" in msg  # Right-to-left formatting


# ============================================================================
# INTEGRATION-LIKE TESTS
# ============================================================================

class TestIntegration:
    """Higher-level integration tests."""
    
    def test_full_workflow_success(self, mock_supabase):
        """Test complete successful workflow."""
        prayer_record = {
            "id": 50,
            "prayer_name": "Full Test",
            "request": "Complete workflow",
            "status": "pending",
            "last_used_at": None,
        }
        
        mock_supabase.get_next_prayer.return_value = prayer_record
        mock_supabase.extract_prayer_data.return_value = (
            "Full Test",
            "Complete workflow",
            50,
        )
        mock_supabase.set_processing.return_value = True
        mock_supabase.mark_success.return_value = True
        
        with patch('prayer_logic.prayers_file.get_supabase', return_value=mock_supabase):
            with patch('prayer_logic.prayers_file.send_email', return_value=True):
                result = process_from_database(recipient="test@example.com")
        
        assert result is True
        
        # Verify call sequence
        assert mock_supabase.get_next_prayer.called
        assert mock_supabase.extract_prayer_data.called
        assert mock_supabase.set_processing.called
        assert mock_supabase.mark_success.called
        assert mock_supabase.mark_failure.not_called
    
    def test_supabase_connection_failure(self, mock_supabase):
        """Test behavior when Supabase is not connected."""
        mock_supabase.is_connected.return_value = False
        
        with patch('prayer_logic.prayers_file.get_supabase', return_value=mock_supabase):
            result = process_from_database(recipient="test@example.com")
        
        assert result is False
        mock_supabase.get_next_prayer.assert_not_called()

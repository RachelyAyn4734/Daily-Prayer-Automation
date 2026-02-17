#!/usr/bin/env python3
"""
Daily prayer sending cron job for Render.com
Sends the next prayer via email using the async prayer service.
"""
import asyncio
import sys
import os
import logging
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.prayer_service import get_prayer_service
from app.core.supabase_client import cleanup_supabase
from app.settings import validate_config, DEFAULT_RECIPIENT

# Configure logging for cron job
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

log = logging.getLogger(__name__)

async def send_daily_prayer():
    """Send the daily prayer via email."""
    log.info("🙏 Starting daily prayer cron job...")
    
    try:
        # Validate configuration
        if not validate_config():
            log.error("❌ Configuration validation failed")
            return False
        
        # Get prayer service
        prayer_service = await get_prayer_service(data_mode="database")
        
        # Check service health
        status = await prayer_service.get_service_status()
        if not status.get("storage_healthy"):
            log.error("❌ Prayer service unhealthy: %s", status.get("error"))
            return False
        
        log.info("✅ Prayer service healthy, prayer count: %d", status.get("prayer_count", 0))
        
        # Process and send prayer
        recipient = DEFAULT_RECIPIENT or os.getenv("CRON_RECIPIENT")
        if not recipient:
            log.error("❌ No recipient configured. Set DEFAULT_RECIPIENT or CRON_RECIPIENT")
            return False
        
        log.info("📧 Sending daily prayer to: %s", recipient)
        result = await prayer_service.process_and_send_prayer(recipient=recipient)
        
        if result["success"]:
            prayer_info = result["prayer"]
            log.info("✅ Daily prayer sent successfully!")
            log.info("   Prayer: %s", prayer_info["name"])
            log.info("   Request: %s", prayer_info.get("request", "N/A"))
            log.info("   ID: %s", prayer_info["id"])
            return True
        else:
            log.error("❌ Failed to send daily prayer: %s", result.get("error"))
            return False
    
    except Exception as e:
        log.error("❌ Unexpected error in daily prayer cron: %s", e, exc_info=True)
        return False
    
    finally:
        # Cleanup connections
        try:
            await cleanup_supabase()
        except Exception as e:
            log.warning("⚠️ Error during cleanup: %s", e)

async def main():
    """Main cron job entry point."""
    start_time = datetime.now()
    log.info("🚀 Daily prayer cron job started at %s", start_time.isoformat())
    
    success = await send_daily_prayer()
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    if success:
        log.info("🎉 Daily prayer cron job completed successfully in %s", duration)
        sys.exit(0)
    else:
        log.error("💥 Daily prayer cron job failed after %s", duration)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Health check script for monitoring the prayer service.
Used by external monitoring services and Render's health checks.
"""
import asyncio
import sys
import os
import json
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.prayer_service import get_prayer_service
from app.core.supabase_client import cleanup_supabase
from app.settings import validate_config

async def check_service_health():
    """
    Comprehensive health check of all service components.
    Returns exit code 0 for healthy, 1 for unhealthy.
    """
    health_status = {
        "timestamp": datetime.now().isoformat(),
        "status": "healthy",
        "components": {},
        "details": {}
    }
    
    try:
        # 1. Configuration validation
        config_valid = validate_config()
        health_status["components"]["configuration"] = "healthy" if config_valid else "unhealthy"
        
        if not config_valid:
            health_status["status"] = "unhealthy"
            health_status["details"]["configuration"] = "Environment variables validation failed"
        
        # 2. Prayer service health
        try:
            prayer_service = await get_prayer_service(data_mode="database")
            service_status = await prayer_service.get_service_status()
            
            if service_status.get("storage_healthy"):
                health_status["components"]["prayer_service"] = "healthy"
                health_status["details"]["prayer_count"] = service_status.get("prayer_count")
                health_status["details"]["storage_mode"] = service_status.get("storage_mode")
            else:
                health_status["components"]["prayer_service"] = "unhealthy"
                health_status["status"] = "unhealthy"
                health_status["details"]["prayer_service_error"] = service_status.get("error")
        
        except Exception as e:
            health_status["components"]["prayer_service"] = "unhealthy"
            health_status["status"] = "unhealthy"
            health_status["details"]["prayer_service_error"] = str(e)
        
        # 3. Database connectivity (via Supabase)
        try:
            # This is implicitly tested by prayer service, but we can add explicit check
            health_status["components"]["database"] = "healthy" if service_status.get("storage_healthy") else "unhealthy"
        except:
            health_status["components"]["database"] = "unknown"
        
        # 4. Email service check (basic validation)
        email_config_keys = ["GMAIL_APP_PASSWORD", "GMAIL_USER"]
        email_configured = all(os.getenv(key) for key in email_config_keys)
        health_status["components"]["email_config"] = "healthy" if email_configured else "unhealthy"
        
        if not email_configured:
            health_status["status"] = "unhealthy"
            health_status["details"]["email_config"] = "Missing email configuration"
    
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["details"]["unexpected_error"] = str(e)
    
    finally:
        # Cleanup
        try:
            await cleanup_supabase()
        except:
            pass
    
    # Output health status as JSON
    print(json.dumps(health_status, indent=2))
    
    # Exit with appropriate code
    if health_status["status"] == "healthy":
        sys.exit(0)
    else:
        sys.exit(1)

async def main():
    """Main health check entry point."""
    await check_service_health()

if __name__ == "__main__":
    asyncio.run(main())
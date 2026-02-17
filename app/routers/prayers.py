"""
Prayer API endpoints with enhanced error handling and async operations.
Refactored to use new prayer service with dependency injection.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any
import logging
from ..core.prayer_service import get_prayer_service, PrayerService
from ..core.email import validate_email_config
from ..schemas import PrayerIn
from ..settings import validate_config, DATA_MODE

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["prayers"])

async def get_prayer_service_dependency() -> PrayerService:
    """Dependency to get prayer service instance."""
    return await get_prayer_service()

@router.post("/add_prayer")
async def add_prayer_endpoint(
    payload: PrayerIn,
    prayer_service: PrayerService = Depends(get_prayer_service_dependency)
):
    """Add a new prayer request with comprehensive validation."""
    try:
        # Validate configuration
        if not validate_config():
            raise HTTPException(
                status_code=500,
                detail="Server configuration error - missing required environment variables"
            )
        
        # Validate input
        if not payload.prayer_name or not payload.prayer_name.strip():
            raise HTTPException(
                status_code=400,
                detail="Prayer name is required and cannot be empty"
            )
        
        # Add prayer
        result = await prayer_service.add_prayer(
            prayer_name=payload.prayer_name,
            request=payload.request,
            phone=payload.phone,
            contact_name=payload.contact_name,
            tag_contact=payload.tag_contact,
            target_list=payload.target_list
        )
        
        if result:
            log.info("Prayer added successfully: %s (ID: %s)", payload.prayer_name, result)
            return {
                "status": "success",
                "data": {
                    "id": result,
                    "prayer_name": payload.prayer_name,
                    "target_list": payload.target_list
                },
                "message": "Prayer added successfully"
            }
        else:
            log.error("Failed to add prayer: %s", payload.prayer_name)
            raise HTTPException(
                status_code=500,
                detail="Failed to save prayer to storage"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        log.error("Unexpected error adding prayer %s: %s", payload.prayer_name, e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/send_prayer")
async def send_prayer_endpoint(
    recipient: Optional[str] = None,
    target_list: str = "default",
    prayer_service: PrayerService = Depends(get_prayer_service_dependency)
):
    """Send the next prayer via email using circular iteration with detailed results."""
    try:
        # Validate configuration
        if not validate_config():
            raise HTTPException(
                status_code=500,
                detail="Server configuration error - missing required environment variables"
            )
        
        if not validate_email_config():
            raise HTTPException(
                status_code=500,
                detail="Email configuration error - check SENDER_EMAIL and SENDER_PASSWORD"
            )
        
        # Process and send prayer
        result = await prayer_service.process_and_send_prayer(recipient, target_list)
        
        if result["success"]:
            return {
                "status": "success",
                "data": {
                    "prayer": result["prayer"],
                    "email_sent": result["email_sent"],
                    "storage_updated": result.get("storage_updated", False)
                },
                "message": "Prayer sent successfully"
            }
        else:
            error_detail = result.get("error", "Unknown error occurred")
            log.error("Prayer sending failed: %s", error_detail)
            
            # Return detailed error information
            return {
                "status": "error",
                "data": {
                    "prayer": result.get("prayer"),
                    "email_sent": result.get("email_sent", False),
                    "storage_updated": result.get("storage_updated", False),
                    "error": error_detail
                },
                "message": "Prayer processing failed"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        log.error("Unexpected error sending prayer: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/next_prayer")
async def get_next_prayer_endpoint(
    target_list: str = "default",
    prayer_service: PrayerService = Depends(get_prayer_service_dependency)
):
    """Get the next prayer without sending email (preview mode)."""
    try:
        prayer_data = await prayer_service.get_next_prayer(target_list)
        
        if prayer_data:
            name, request, prayer_id = prayer_data
            return {
                "status": "success",
                "data": {
                    "prayer": {
                        "name": name,
                        "request": request,
                        "id": prayer_id
                    },
                    "target_list": target_list
                },
                "message": "Next prayer retrieved successfully"
            }
        else:
            return {
                "status": "success",
                "data": {
                    "prayer": None,
                    "target_list": target_list
                },
                "message": "No prayers available"
            }
    
    except Exception as e:
        log.error("Failed to get next prayer: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving prayer: {str(e)}"
        )

@router.get("/stats")
async def get_stats_endpoint(
    target_list: str = "default",
    prayer_service: PrayerService = Depends(get_prayer_service_dependency)
):
    """Get comprehensive prayer and service statistics."""
    try:
        prayer_count = await prayer_service.get_prayer_count(target_list)
        service_status = await prayer_service.get_service_status()
        
        return {
            "status": "success",
            "data": {
                "prayer_stats": {
                    "total_prayers": prayer_count,
                    "target_list": target_list
                },
                "service_status": service_status,
                "configuration": {
                    "data_mode": DATA_MODE
                }
            },
            "message": "Statistics retrieved successfully"
        }
    
    except Exception as e:
        log.error("Failed to get stats: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving stats: {str(e)}"
        )

@router.get("/health")
async def health_check(
    prayer_service: PrayerService = Depends(get_prayer_service_dependency)
):
    """Comprehensive health check endpoint."""
    try:
        config_valid = validate_config()
        email_valid = validate_email_config()
        service_status = await prayer_service.get_service_status()
        
        # Determine overall health
        overall_health = (
            config_valid and 
            email_valid and 
            service_status.get("storage_healthy", False)
        )
        
        health_data = {
            "status": "healthy" if overall_health else "degraded",
            "checks": {
                "config_valid": config_valid,
                "email_config_valid": email_valid,
                "storage_healthy": service_status.get("storage_healthy", False),
                "storage_type": service_status.get("storage_type", "unknown")
            },
            "service_info": {
                "data_mode": DATA_MODE,
                "prayer_count": service_status.get("prayer_count", 0)
            }
        }
        
        # Add database connectivity if applicable
        if "database_connected" in service_status:
            health_data["checks"]["database_connected"] = service_status["database_connected"]
        
        return {
            "status": "success",
            "data": health_data,
            "message": f"Health check complete - {health_data['status']}"
        }
    
    except Exception as e:
        log.error("Health check failed: %s", e, exc_info=True)
        return {
            "status": "error",
            "data": {
                "status": "unhealthy",
                "error": str(e)
            },
            "message": "Health check failed"
        }
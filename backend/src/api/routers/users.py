"""Users router."""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any
import logging

from ...models.user import UserPreferences, UserProfileUpdate
from ...services.dynamodb import db_service
from ...middleware.auth_middleware import require_auth
from ...middleware.error_handler import ValidationError, ResourceNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.put("/profile")
async def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Update user profile."""
    try:
        updates = profile_data.dict(exclude_unset=True)
        
        updated_user = await db_service.update_user(current_user["user_id"], updates)
        
        return {
            "message": "Profile updated successfully",
            "user": {
                "user_id": updated_user["user_id"],
                "email": updated_user["email"],
                "full_name": updated_user.get("full_name"),
                "age": updated_user.get("age"),
                "profession": updated_user.get("profession"),
                "education_level": updated_user.get("education_level"),
                "country": updated_user.get("country"),
                "onboarding_completed": updated_user.get("onboarding_completed", False),
                "preferences": updated_user.get("preferences"),
                "updated_at": updated_user["updated_at"]
            }
        }
    except (ValidationError, ResourceNotFoundError):
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )

@router.post("/onboarding")
async def complete_onboarding(
    onboarding_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Complete user onboarding."""
    try:
        # Extract profile updates
        profile_updates = {
            "full_name": onboarding_data.get("full_name"),
            "age": onboarding_data.get("age"),
            "profession": onboarding_data.get("profession"),
            "education_level": onboarding_data.get("education_level"),
            "country": onboarding_data.get("country"),
            "onboarding_completed": True
        }
        
        # Remove None values
        profile_updates = {k: v for k, v in profile_updates.items() if v is not None}
        
        # Add learning preferences directly to profile updates
        if onboarding_data.get("learning_style"):
            profile_updates["learning_style"] = onboarding_data.get("learning_style")
        
        if onboarding_data.get("attention_span"):
            profile_updates["attention_span"] = onboarding_data.get("attention_span")
        
        if onboarding_data.get("difficulty_level"):
            profile_updates["difficulty_level"] = onboarding_data.get("difficulty_level")
        
        # Also store in preferences object for backward compatibility
        preferences = {
            "learning_style": onboarding_data.get("learning_style"),
            "attention_span": onboarding_data.get("attention_span"),
            "difficulty_level": onboarding_data.get("difficulty_level")
        }
        
        # Remove None values from preferences
        preferences = {k: v for k, v in preferences.items() if v is not None}
        
        # Add preferences to profile updates
        if preferences:
            profile_updates["preferences"] = preferences
        
        # Update user profile
        updated_user = await db_service.update_user(current_user["user_id"], profile_updates)
        
        logger.info(f"Onboarding completed for user: {current_user['user_id']}")
        
        return {
            "message": "Onboarding completed successfully",
            "user": {
                "user_id": updated_user["user_id"],
                "email": updated_user["email"],
                "full_name": updated_user.get("full_name"),
                "age": updated_user.get("age"),
                "profession": updated_user.get("profession"),
                "education_level": updated_user.get("education_level"),
                "country": updated_user.get("country"),
                "onboarding_completed": updated_user.get("onboarding_completed", False),
                "preferences": updated_user.get("preferences"),
                "updated_at": updated_user["updated_at"]
            }
        }
    except (ValidationError, ResourceNotFoundError):
        raise
    except Exception as e:
        logger.error(f"Error completing onboarding: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete onboarding"
        )
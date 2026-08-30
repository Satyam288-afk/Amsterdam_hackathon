"""
Authentication Dependency using Supabase SDK
Allows FastAPI routes to securely verify users logged in via Google OAuth
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
import logging

from config import settings

logger = logging.getLogger(__name__)

# Initialize the official Supabase client
# Safe-guarding in case keys are not configured
supabase_client: Client = None

if settings.supabase_url and settings.supabase_service_role_key:
    try:
        supabase_client = create_client(settings.supabase_url, settings.supabase_service_role_key)
        logger.info("✅ Supabase Auth Client initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase Auth Client: {e}")

# Security scheme to extract Bearer token from header
security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict:
    """
    Dependency to verify a JWT access token using the official Supabase SDK.
    Injects the validated user dictionary into secure endpoints.
    """
    if not supabase_client:
        logger.error("Supabase Auth Client is uninitialized. Check environment variables.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is currently unavailable."
        )

    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")
    token = credentials.credentials

    try:
        # Call Supabase SDK to verify the JWT token
        response = supabase_client.auth.get_user(token)
        user = response.user

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session token."
            )

        # Convert User object properties to standard dictionary format for easy route usage
        app_metadata = user.app_metadata or {}
        return {
            "id": user.id,
            "email": user.email,
            # recovery_role is privileged app metadata. Do not use user_metadata
            # here because a browser client can modify it.
            "role": app_metadata.get("recovery_role", "user"),
            "app_metadata": app_metadata,
            "user_metadata": user.user_metadata,
            "created_at": user.created_at
        }

    except Exception as e:
        logger.warning(f"Failed JWT validation attempt: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid."
        )


async def require_recovery_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict:
    """Require a verified Supabase session only when production auth is enabled.

    Keeping this switch off preserves the credential-free fictional demo; a
    deployment must set AUTH_REQUIRED=true together with Supabase credentials.
    """
    if not settings.auth_required:
        return {"id": "offline-demo", "email": "offline-demo@sambhaash.local", "role": "admin", "demo_mode": True}
    return await get_current_user(credentials)


async def require_recovery_admin(current_user: dict = Depends(require_recovery_user)) -> dict:
    """Server-side administrator boundary for any state-changing recovery action."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required for recovery operations.")
    return current_user

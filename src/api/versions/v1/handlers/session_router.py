from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from src.api.dependencies import (
    get_current_user,
    get_current_user_token,
    get_session_repository,
    get_user_repository,
)
from src.dtos.user_dtos import (
    UpdateEmailNotificationsRequest,
    UpdateSessionNotificationsRequest,
)
from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import SessionRepository, UserRepository
from src.models import User
from src.types import AccessToken
from src.types.common_types import DeviceID, SessionId

logger = get_logger(__name__)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("")
async def get_sessions(
    token: AccessToken = Depends(get_current_user_token),
    session_repo: SessionRepository = Depends(get_session_repository),
):
    sessions = await session_repo.get_user_sessions(token.user_id.clean())
    current_session_id = token.session_id
    return [
        {
            "id": s.get_prefixed_id(),
            "is_current": s.get_prefixed_id() == current_session_id,
            "platform": s.platform,
            "device_id": s.device_id,
            "device_model": s.device_model,
            "device_brand": s.device_brand,
            "os_version": s.os_version,
            "ip_address": s.ip_address,
            "country": s.country,
            "city": s.city,
            "allow_notifications": s.allow_notifications,
            "last_seen_at": s.last_seen_at,
            "created_at": s.created_at,
        }
        for s in sessions
    ]


@router.delete("/{session_id}")
async def revoke_session(
    session_id: SessionId,
    token: AccessToken = Depends(get_current_user_token),
    session_repo: SessionRepository = Depends(get_session_repository),
):
    # Prevent revoking the current session — use /auth/logout for that
    if str(session_id) == token.session_id.clean() or session_id == token.session_id:
        return JSONResponse(
            status_code=400,
            content={
                "message": "Cannot revoke your current session. Use /auth/logout instead."
            },
        )

    session, err = await session_repo.get_session(token.session_id.clean())
    if err or not session:
        return JSONResponse(status_code=404, content={"message": "Session not found"})

    if str(session.user_id) != token.user_id.clean():
        return JSONResponse(status_code=403, content={"message": "Forbidden"})

    err = await session_repo.revoke_session(session_id.clean())
    if err:
        logger.error("Failed to revoke session %s: %s", session_id, err)
        return JSONResponse(
            status_code=500, content={"message": "Failed to revoke session"}
        )

    return {"message": "Session revoked successfully"}


@router.patch("/{session_id}/notifications")
async def update_session_notifications(
    session_id: SessionId,
    body: UpdateSessionNotificationsRequest,
    user: User = Depends(get_current_user),
    device_id: DeviceID = Header(..., alias="X-Device-ID"),
    session_repo: SessionRepository = Depends(get_session_repository),
):
    session, err = await session_repo.get_session(session_id.clean())
    if err or not session:
        return JSONResponse(status_code=404, content={"message": "Session not found"})

    if session.user_id != user.id:
        return JSONResponse(status_code=403, content={"message": "Forbidden"})

    if session.device_id != device_id:
        return JSONResponse(status_code=403, content={"message": "Device mismatch"})

    session.allow_notifications = body.allow_notifications
    session.fcm_token = body.fcm_token if body.allow_notifications else None

    _, err = await session_repo.update(session)
    if err:
        logger.error(
            "Failed to update notifications for session %s: %s", session_id, err
        )
        return JSONResponse(
            status_code=500, content={"message": "Failed to update session"}
        )

    return {"message": "Notifications updated successfully"}


@router.patch("/notifications/email")
async def update_email_notifications(
    body: UpdateEmailNotificationsRequest,
    user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
):
    _, err = await user_repo.update_user(
        user_id=user.id, email_notifications=body.email_notifications
    )
    if err:
        logger.error(
            "Failed to update email notifications for user %s: %s", user.id, err
        )
        return JSONResponse(status_code=500, content={"message": "Failed to update"})

    return {"message": "Email notifications updated successfully"}

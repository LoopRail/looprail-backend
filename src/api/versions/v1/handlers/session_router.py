from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from src.api.dependencies import get_current_user, get_session_repository, get_user_repository
from src.dtos.user_dtos import UpdateEmailNotificationsRequest, UpdateSessionNotificationsRequest
from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import SessionRepository, UserRepository
from src.models import User
from src.types.common_types import DeviceID, SessionId

logger = get_logger(__name__)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


class UpdateNotificationsRequest(BaseModel):
    allow_notifications: bool
    fcm_token: str | None = None


@router.patch("/{session_id}/notifications")
async def update_session_notifications(
    session_id: SessionId,
    body: UpdateSessionNotificationsRequest,
    user: User = Depends(get_current_user),
    device_id: DeviceID = Header(..., alias="X-Device-ID"),
    session_repo: SessionRepository = Depends(get_session_repository),
):
    session, err = await session_repo.get_session(session_id)
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
        logger.error("Failed to update notifications for session %s: %s", session_id, err)
        return JSONResponse(status_code=500, content={"message": "Failed to update session"})

    return {"message": "Notifications updated successfully"}


@router.patch("/notifications/email")
async def update_email_notifications(
    body: UpdateEmailNotificationsRequest,
    user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
):
    user.email_notifications = body.email_notifications
    _, err = await user_repo.update(user)
    if err:
        logger.error("Failed to update email notifications for user %s: %s", user.id, err)
        return JSONResponse(status_code=500, content={"message": "Failed to update"})

    return {"message": "Email notifications updated successfully"}

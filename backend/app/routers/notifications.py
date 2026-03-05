from fastapi import APIRouter, Depends

from app.models import User
from app.schemas import NotificationRequest
from app.auth import get_current_user
from app.services.notification_service import send_sms, send_email

router = APIRouter()


@router.post("/sms")
async def notify_sms(
    data: NotificationRequest,
    current_user: User = Depends(get_current_user),
):
    result = send_sms(recipient=data.recipient, message=data.message)
    return {"status": "sent", "channel": "sms", **result}


@router.post("/email")
async def notify_email(
    data: NotificationRequest,
    current_user: User = Depends(get_current_user),
):
    result = send_email(recipient=data.recipient, message=data.message)
    return {"status": "sent", "channel": "email", **result}

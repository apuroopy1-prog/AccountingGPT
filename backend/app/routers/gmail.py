"""
Gmail OAuth2 router.

  GET    /gmail/auth-url     — get Google OAuth authorization URL
  GET    /gmail/callback     — OAuth callback (redirects back to frontend)
  GET    /gmail/status       — check if current user has Gmail connected
  DELETE /gmail/disconnect   — revoke and delete Gmail credentials
"""
import os
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth import get_current_user
from app.database import get_db
from app.models import GmailCredentials, User

router = APIRouter()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


@router.get("/auth-url")
async def get_auth_url(current_user: User = Depends(get_current_user)):
    """Return Google OAuth2 authorization URL for the current user."""
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    if not client_id:
        raise HTTPException(status_code=503, detail="Gmail integration not configured")

    from app.services.gmail_service import get_auth_url
    url = get_auth_url(current_user.id)
    return {"url": url}


@router.get("/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Google OAuth2 callback.
    Exchanges code for tokens, stores in DB, redirects to frontend invoices page.
    """
    try:
        user_id = int(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    from app.services.gmail_service import exchange_code

    try:
        tokens = exchange_code(code, user_id)
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/invoices?gmail=error")

    # Upsert credentials
    result = await db.execute(
        select(GmailCredentials).where(GmailCredentials.user_id == user_id)
    )
    creds = result.scalar_one_or_none()

    if creds is None:
        creds = GmailCredentials(user_id=user_id, **tokens)
        db.add(creds)
    else:
        creds.access_token = tokens["access_token"]
        creds.refresh_token = tokens["refresh_token"]
        creds.token_expiry = tokens["token_expiry"]

    await db.commit()
    return RedirectResponse(f"{FRONTEND_URL}/invoices?gmail=connected")


@router.get("/status")
async def gmail_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GmailCredentials).where(GmailCredentials.user_id == current_user.id)
    )
    creds = result.scalar_one_or_none()
    if creds is None:
        return {"connected": False, "last_checked": None}
    return {
        "connected": True,
        "last_checked": creds.last_checked_at.isoformat() if creds.last_checked_at else None,
    }


@router.delete("/disconnect")
async def disconnect_gmail(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GmailCredentials).where(GmailCredentials.user_id == current_user.id)
    )
    creds = result.scalar_one_or_none()
    if creds:
        await db.delete(creds)
        await db.commit()
    return {"message": "Gmail disconnected"}

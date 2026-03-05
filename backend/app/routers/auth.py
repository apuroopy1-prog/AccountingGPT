import os
import secrets
import hashlib
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.models import User, PasswordResetToken
from app.schemas import UserRegister, UserLogin, Token, UserOut, PasswordChange, ForgotPasswordRequest, ResetPasswordRequest, UserUpdate
from app.auth import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, verify_refresh_token, get_current_user,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.email_utils import send_reset_email

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

REFRESH_COOKIE_NAME = "refresh_token"
COOKIE_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # seconds


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    is_prod = os.getenv("ENV", "development") == "production"
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        samesite="lax",
        secure=is_prod,
        max_age=COOKIE_MAX_AGE,
        path="/api/auth",
    )


@router.post("/register", response_model=Token)
@limiter.limit("5/minute")
async def register(request: Request, response: Response, data: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    raw_refresh, hashed_refresh = create_refresh_token(user.id)
    user.refresh_token_hash = hashed_refresh
    await db.commit()

    _set_refresh_cookie(response, raw_refresh)
    access_token = create_access_token({"sub": str(user.id)})
    return Token(access_token=access_token)


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(request: Request, response: Response, data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    raw_refresh, hashed_refresh = create_refresh_token(user.id)
    user.refresh_token_hash = hashed_refresh
    await db.commit()

    _set_refresh_cookie(response, raw_refresh)
    access_token = create_access_token({"sub": str(user.id)})
    return Token(access_token=access_token)


@router.post("/refresh", response_model=Token)
async def refresh(request: Request, db: AsyncSession = Depends(get_db)):
    raw_cookie = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_cookie:
        raise HTTPException(status_code=401, detail="No refresh token")

    try:
        user_id_str, token_part = raw_cookie.split(":", 1)
        user_id = int(user_id_str)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.refresh_token_hash:
        raise HTTPException(status_code=401, detail="Session expired")

    if not verify_refresh_token(token_part, user.refresh_token_hash):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access_token = create_access_token({"sub": str(user.id)})
    return Token(access_token=access_token)


@router.post("/logout")
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.refresh_token_hash = None
    await db.commit()
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/api/auth", httponly=True, samesite="lax")
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    # Always respond the same way to prevent email enumeration
    if user:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.utcnow() + timedelta(minutes=15)

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset_token)
        await db.commit()

        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        reset_link = f"{frontend_url}/reset-password?token={raw_token}"
        await send_reset_email(user.email, reset_link)

    return {"detail": "If that email is registered, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hashlib.sha256(data.token.encode()).hexdigest()
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used == False,  # noqa: E712
            PasswordResetToken.expires_at > datetime.utcnow(),
        )
    )
    reset_token = result.scalar_one_or_none()
    if not reset_token:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    result = await db.execute(select(User).where(User.id == reset_token.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    user.hashed_password = hash_password(data.new_password)
    reset_token.used = True
    await db.commit()
    return {"detail": "Password reset successfully"}


@router.put("/profile", response_model=UserOut)
async def update_profile(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.currency is not None:
        current_user.currency = data.currency
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.put("/password")
async def change_password(
    data: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = hash_password(data.new_password)
    await db.commit()
    return {"detail": "Password updated successfully"}

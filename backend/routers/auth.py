"""
routers/auth.py – Authentication endpoints.

POST /auth/login    – username + password → access + refresh tokens
POST /auth/refresh  – refresh token → new access token
GET  /auth/me       – current user info (requires valid access token)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth_deps import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    verify_password,
)
from database import db

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Request / Response models ─────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    role:          str
    username:      str

class RefreshRequest(BaseModel):
    refresh_token: str

class AccessTokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, email, hashed_password, role, is_active FROM users WHERE username = %s",
                (body.username,),
            )
            user = cur.fetchone()

    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    return TokenResponse(
        access_token=create_access_token(user["id"], user["username"], user["role"]),
        refresh_token=create_refresh_token(user["id"]),
        role=user["role"],
        username=user["username"],
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(body: RefreshRequest):
    payload = decode_token(body.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, role, is_active FROM users WHERE id = %s",
                (int(user_id),),
            )
            user = cur.fetchone()

    if not user or not user["is_active"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return AccessTokenResponse(
        access_token=create_access_token(user["id"], user["username"], user["role"]),
    )


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return {
        "id":       current_user["id"],
        "username": current_user["username"],
        "email":    current_user["email"],
        "role":     current_user["role"],
    }

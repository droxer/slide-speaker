"""Authentication routes providing registration and login for NextAuth."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from slidespeaker.repository.user import (
    create_user_with_password,
    upsert_oauth_user,
    verify_user_credentials,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class CredentialsPayload(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class OAuthPayload(BaseModel):
    email: EmailStr
    id: str | None = None
    name: str | None = None
    picture: str | None = None


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(payload: CredentialsPayload) -> dict[str, object]:
    try:
        user = await create_user_with_password(
            email=payload.email,
            password=payload.password,
            name=payload.name,
        )
    except ValueError as exc:  # email already exists
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return {"user": user}


@router.post("/login")
async def login_user(payload: CredentialsPayload) -> dict[str, object]:
    user = await verify_user_credentials(email=payload.email, password=payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials"
        )
    return {"user": user}


@router.post("/oauth/google")
async def oauth_google(payload: OAuthPayload) -> dict[str, object]:
    try:
        user = await upsert_oauth_user(payload.dict())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return {"user": user}

"""Authentication routes providing registration and login for NextAuth."""

from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from slowapi import Limiter
from slowapi.util import get_remote_address

from slidespeaker.repository.user import (
    create_user_with_password,
    upsert_oauth_user,
    verify_user_credentials,
)

# Create a rate limiter for this router
limiter = Limiter(key_func=get_remote_address)

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
@limiter.limit("5/minute")  # Limit to 5 registrations per minute per IP
async def register_user(
    request: Request,
    payload: Annotated[CredentialsPayload, Body(...)],
) -> dict[str, object]:
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
@limiter.limit("10/minute")  # Limit to 10 login attempts per minute per IP
async def login_user(
    request: Request,
    payload: Annotated[CredentialsPayload, Body(...)],
) -> dict[str, object]:
    user = await verify_user_credentials(email=payload.email, password=payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials"
        )
    return {"user": user}


@router.post("/oauth/google")
@limiter.limit("10/minute")  # Limit to 10 OAuth attempts per minute per IP
async def oauth_google(
    request: Request,
    payload: Annotated[OAuthPayload, Body(...)],
) -> dict[str, object]:
    try:
        user = await upsert_oauth_user(payload.dict())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return {"user": user}

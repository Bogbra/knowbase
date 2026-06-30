import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_dep, get_redis_dep
from app.core.limiter import limiter
from app.db.models.user import User
from app.db.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _service(
    db: AsyncSession = Depends(get_db_dep),
    redis: aioredis.Redis = Depends(get_redis_dep),
) -> AuthService:
    return AuthService(UserRepository(db), redis)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    service: AuthService = Depends(_service),
) -> TokenResponse:
    _, tokens = await service.register(body.email, body.password)
    return tokens


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    service: AuthService = Depends(_service),
) -> TokenResponse:
    return await service.login(body.email, body.password)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh(
    request: Request,
    body: RefreshRequest,
    service: AuthService = Depends(_service),
) -> TokenResponse:
    return await service.refresh(body.refresh_token)


@router.delete("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest,
    service: AuthService = Depends(_service),
) -> None:
    await service.logout(body.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)

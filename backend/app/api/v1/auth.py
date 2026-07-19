import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_dep, get_redis_dep
from app.core.limiter import limiter
from app.db.models.user import User
from app.db.repositories.user_repository import UserRepository
from app.schemas.account import DeleteAccountRequest, ExportResponse
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.account_service import AccountService
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


def _account_service(
    db: AsyncSession = Depends(get_db_dep),
    redis: aioredis.Redis = Depends(get_redis_dep),
) -> AccountService:
    return AccountService(db, redis)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("3/minute")
async def delete_account(
    request: Request,
    body: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_dep),
    service: AccountService = Depends(_account_service),
) -> None:
    """Permanently delete the authenticated account.

    Workspace handling (three-case rule):
    1. Workspaces where the user is the sole member — deleted entirely (cascade).
    2. Shared workspaces where user is NOT owner — membership removed; workspace survives.
    3. Shared workspaces where user IS owner — 409 returned; transfer ownership first.

    S3 files from deleted workspaces are removed best-effort after the DB commit.
    Redis event-streams (sse:run:*) expire via TTL within 1 h and are not actively purged.
    """
    from app.core import storage as s3

    s3_keys = await service.delete_account(current_user, body.password)
    await db.commit()

    for key in s3_keys:
        try:
            await s3.delete_file(key)
        except Exception:
            import logging

            logging.getLogger(__name__).warning(
                "s3_delete_failed_on_account_delete", extra={"key": key}
            )


@router.get("/me/export", response_model=ExportResponse)
@limiter.limit("5/minute")
async def export_account(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: AccountService = Depends(_account_service),
) -> ExportResponse:
    """Export all user-generated data as JSON (GDPR data portability, Art. 20).

    Includes: profile, workspace memberships, conversations + messages, memories,
    document metadata, and API key metadata. File contents and key hashes are never
    exported.
    """
    return await service.export_account(current_user)

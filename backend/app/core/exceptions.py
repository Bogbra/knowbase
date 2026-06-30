from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, status_code: int, error_type: str, title: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.error_type = error_type
        self.title = title
        self.detail = detail


class EmailAlreadyExistsError(AppError):
    def __init__(self, email: str) -> None:
        super().__init__(
            status_code=409,
            error_type="email-already-exists",
            title="Email already registered",
            detail=f"{email} is already registered",
        )


class InvalidCredentialsError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            error_type="invalid-credentials",
            title="Invalid credentials",
            detail="Email or password is incorrect",
        )


class InvalidTokenError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            error_type="invalid-token",
            title="Invalid or expired token",
            detail="The provided token is invalid or has expired",
        )


class UserInactiveError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            error_type="user-inactive",
            title="Account deactivated",
            detail="This account has been deactivated",
        )


class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(
            status_code=404,
            error_type="not-found",
            title="Resource not found",
            detail=f"{resource} {resource_id} not found",
        )


class ForbiddenError(AppError):
    def __init__(self, detail: str = "Insufficient permissions") -> None:
        super().__init__(
            status_code=403,
            error_type="forbidden",
            title="Forbidden",
            detail=detail,
        )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": f"https://knowbase.dev/errors/{exc.error_type}",
            "title": exc.title,
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": str(request.url.path),
        },
    )

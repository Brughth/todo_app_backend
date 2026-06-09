from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    def __init__(self, status_code: int, detail: str | dict, code: str | None = None):
        self.status_code = status_code
        self.detail = detail
        self.code = code


class NotFoundException(AppException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status.HTTP_404_NOT_FOUND,
            {"code": "NOT_FOUND", "message": f"{resource} not found."},
        )


class ForbiddenException(AppException):
    def __init__(self, message: str = "Access denied."):
        super().__init__(
            status.HTTP_403_FORBIDDEN,
            {"code": "FORBIDDEN", "message": message},
        )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."},
        )

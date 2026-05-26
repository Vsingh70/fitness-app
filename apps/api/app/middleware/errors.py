from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.logging_config import get_logger

log = get_logger("errors")


ERROR_CODE_BY_STATUS: dict[int, str] = {
    400: "validation_error",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    503: "integration_error",
}


def _envelope(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def on_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_envelope(
                code="validation_error",
                message="Request validation failed.",
                details={"errors": exc.errors()},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def on_http_exception(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = ERROR_CODE_BY_STATUS.get(exc.status_code, "internal_error")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        details = exc.detail if not isinstance(exc.detail, str) else None
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(code=code, message=message, details=details),
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def on_unhandled(_request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_exception", error=str(exc))
        return JSONResponse(
            status_code=500,
            content=_envelope(
                code="internal_error",
                message="An internal error occurred.",
            ),
        )

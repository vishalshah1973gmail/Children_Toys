"""Typed error helpers and global exception handlers."""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


def api_error(
    status_code: int,
    code: str,
    message: str,
    field: str | None = None,
) -> HTTPException:
    """Build an HTTPException whose detail matches the ErrorDetail schema."""
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, "field": field},
    )


def not_found(resource: str) -> HTTPException:
    """404 helper."""
    return api_error(status.HTTP_404_NOT_FOUND, "not_found", f"{resource} not found")


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers that normalise every error body to {'error': {...}}."""

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail:
            body = {"error": detail}
        else:
            body = {
                "error": {
                    "code": f"http_{exc.status_code}",
                    "message": str(detail),
                    "field": None,
                }
            }
        return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        location = first.get("loc", [])
        field = ".".join(str(part) for part in location[1:]) or None
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "validation_error",
                    "message": first.get("msg", "Invalid request body"),
                    "field": field,
                }
            },
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_handler(_: Request, exc: IntegrityError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": {
                    "code": "conflict",
                    "message": "The request conflicts with existing data",
                    "field": None,
                }
            },
        )

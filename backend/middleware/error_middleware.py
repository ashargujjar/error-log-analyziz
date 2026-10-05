import json
from typing import Any

from fastapi.responses import JSONResponse
from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from models.models import APIKey


ERROR_PATH = "/errors"


class ErrorAPIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method != "POST" or request.url.path != ERROR_PATH:
            return await call_next(request)

        raw_key = self._authorization_key(request.headers.get("Authorization"))
        if raw_key is None:
            return JSONResponse(
                {"detail": "A valid API key is required."},
                status_code=401,
            )

        user = await APIKey().find_user_by_key(raw_key)
        if (
            user is None
            or not user.get("github_id")
            or not user.get("name")
        ):
            return JSONResponse(
                {"detail": "A valid API key is required."},
                status_code=401,
            )

        try:
            payload = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JSONResponse(
                {"detail": "Request body must be valid JSON."},
                status_code=400,
            )

        if not isinstance(payload, dict):
            return JSONResponse(
                {"detail": "Request body must be a JSON object."},
                status_code=400,
            )

        payload["github_id"] = user["github_id"]
        payload["name"] = user["name"]
        self._replace_request_body(request, payload)

        return await call_next(request)

    @staticmethod
    def _authorization_key(authorization: str | None) -> str | None:
        if not authorization:
            return None

        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        if len(parts) == 1:
            return parts[0]
        return None

    @staticmethod
    def _replace_request_body(request: Request, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        request._body = body
        headers = MutableHeaders(scope=request.scope)
        headers["content-type"] = "application/json"
        headers["content-length"] = str(len(body))

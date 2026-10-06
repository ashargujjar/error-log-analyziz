from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from models.api_key_model import APIKey


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

        request.state.github_id = user["github_id"]
        request.state.api_key_name = user["name"]

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

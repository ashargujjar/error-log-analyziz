from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from models.user_model import User


PUBLIC_PATHS = {
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/auth/"):
            return await call_next(request)

        # Log ingestion is authenticated by an API key in ErrorAPIKeyMiddleware.
        if request.method == "POST" and request.url.path == "/errors":
            return await call_next(request)

        user = await User().get_user_for_session(
            request.cookies.get("auth_session")
        )
        if user is None:
            return JSONResponse(
                {"detail": "Authentication required."},
                status_code=401,
            )

        request.state.user = user
        request.state.github_id = user["github_id"]
        return await call_next(request)

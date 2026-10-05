from fastapi import APIRouter, Cookie, Query

from controllers.github_auth_controller import github_callback, github_login, logout


router = APIRouter(prefix="/auth", tags=["auth"])


router.add_api_route("/github/login", github_login, methods=["GET"])
router.add_api_route("/logout", logout, methods=["POST"])


@router.get("/github/callback")
async def github_oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    github_oauth_state: str | None = Cookie(default=None),
):
    return await github_callback(
        code=code,
        state=state,
        error=error,
        github_oauth_state=github_oauth_state,
    )

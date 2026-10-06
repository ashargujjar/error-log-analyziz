import secrets

from fastapi import Cookie
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse

from models.user_model import User
from schema.schema import GitHubOAuthAccount, UserSchema
from utils.github_auth_utils import (
    auth_error_redirect,
    auth_success_redirect,
    encrypt_token,
    exchange_code_for_token,
    fetch_github_user,
    fetch_primary_email,
    github_authorization_url,
    oauth_cookie_secure,
    token_expires_at,
)


async def github_login() -> RedirectResponse:
    state = secrets.token_urlsafe(32)

    response = RedirectResponse(
        github_authorization_url(state),
        status_code=302,
    )
    response.set_cookie(
        "github_oauth_state",
        state,
        httponly=True,
        max_age=600,
        samesite="lax",
        secure=oauth_cookie_secure(),
    )
    return response


async def github_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    github_oauth_state: str | None = None,
) -> RedirectResponse:
    if error:
        return auth_error_redirect(error)

    if not code or not state:
        return auth_error_redirect("missing_code_or_state")

    if not github_oauth_state or not secrets.compare_digest(
        state,
        github_oauth_state,
    ):
        return auth_error_redirect("invalid_state")

    token_data = await exchange_code_for_token(code)
    access_token = token_data.get("access_token")
    if not access_token:
        return auth_error_redirect("missing_access_token")

    github_user = await fetch_github_user(access_token)
    github_id = github_user.get("id")
    username = github_user.get("login")
    if github_id is None or not username:
        return auth_error_redirect("invalid_github_profile")

    email = github_user.get("email") or await fetch_primary_email(access_token)
    user = UserSchema(
        github_id=str(github_id),
        username=username,
        email=email,
        avatar_url=github_user.get("avatar_url"),
    )
    github_account = GitHubOAuthAccount(
        access_token_encrypted=encrypt_token(access_token),
        refresh_token_encrypted=(
            encrypt_token(token_data["refresh_token"])
            if token_data.get("refresh_token")
            else None
        ),
        token_type=token_data.get("token_type", "bearer"),
        scope=token_data.get("scope"),
        access_token_expires_at=token_expires_at(token_data.get("expires_in")),
        refresh_token_expires_at=token_expires_at(
            token_data.get("refresh_token_expires_in")
        ),
    )

    user_model = User()
    await user_model.save_github_oauth_user(user, github_account)
    session_token = await user_model.create_session(str(github_id))
    return auth_success_redirect(session_token)


async def logout(
    auth_session: str | None = Cookie(default=None),
) -> JSONResponse:
    await User().delete_session(auth_session)

    response = JSONResponse({"message": "Signed out successfully."})
    response.delete_cookie("auth_session")
    response.delete_cookie("github_user_id")
    response.delete_cookie("github_oauth_state")
    return response

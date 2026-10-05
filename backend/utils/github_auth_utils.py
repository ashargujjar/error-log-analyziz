import os
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from cryptography.fernet import Fernet
from fastapi import HTTPException
from fastapi.responses import RedirectResponse


GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise HTTPException(
            status_code=500,
            detail=f"{name} is required for GitHub OAuth.",
        )
    return value


def github_authorization_url(state: str) -> str:
    params = {
        "client_id": required_env("GITHUB_CLIENT_ID"),
        "redirect_uri": github_redirect_uri(),
        "scope": os.getenv("GITHUB_OAUTH_SCOPE", "read:user user:email"),
        "state": state,
        "allow_signup": "true",
    }
    return f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"


def github_redirect_uri() -> str:
    return os.getenv(
        "GITHUB_REDIRECT_URI",
        "http://127.0.0.1:8000/auth/github/callback",
    )


def oauth_cookie_secure() -> bool:
    return os.getenv("OAUTH_COOKIE_SECURE", "false").lower() == "true"


def token_expires_at(seconds: Any) -> datetime | None:
    if seconds is None:
        return None

    try:
        return datetime.utcnow() + timedelta(seconds=int(seconds))
    except (TypeError, ValueError):
        return None


async def exchange_code_for_token(code: str) -> dict[str, Any]:
    payload = {
        "client_id": required_env("GITHUB_CLIENT_ID"),
        "client_secret": required_env("GITHUB_CLIENT_SECRET"),
        "code": code,
        "redirect_uri": github_redirect_uri(),
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            GITHUB_TOKEN_URL,
            data=payload,
            headers={"Accept": "application/json"},
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail="GitHub token exchange failed.",
        )

    token_data = response.json()
    if token_data.get("error"):
        raise HTTPException(status_code=400, detail=token_data["error"])

    return token_data


async def fetch_github_user(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            GITHUB_USER_URL,
            headers=github_headers(access_token),
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail="Could not load GitHub user profile.",
        )

    return response.json()


async def fetch_primary_email(access_token: str) -> str | None:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            GITHUB_EMAILS_URL,
            headers=github_headers(access_token),
        )

    if response.status_code >= 400:
        return None

    emails = response.json()
    for email in emails:
        if email.get("primary") and email.get("verified"):
            return email.get("email")

    return None


def encrypt_token(token: str) -> str:
    key = required_env("GITHUB_TOKEN_ENCRYPTION_KEY")

    try:
        return Fernet(key.encode("ascii")).encrypt(token.encode("utf-8")).decode(
            "ascii"
        )
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=500,
            detail="GITHUB_TOKEN_ENCRYPTION_KEY must be a valid Fernet key.",
        )


def auth_success_redirect(github_id: str) -> RedirectResponse:
    response = RedirectResponse(
        _with_query(
            _frontend_url("success"),
            {
                "auth": "github",
                "login": "success",
            },
        ),
        status_code=302,
    )
    response.delete_cookie("github_oauth_state")
    response.set_cookie(
        "github_user_id",
        github_id,
        httponly=True,
        max_age=60 * 60 * 24 * 30,
        samesite="lax",
        secure=oauth_cookie_secure(),
    )
    return response


def auth_error_redirect(reason: str) -> RedirectResponse:
    response = RedirectResponse(
        _with_query(
            _frontend_url("error"),
            {
                "auth": "github",
                "login": "error",
                "reason": reason,
            },
        ),
        status_code=302,
    )
    response.delete_cookie("github_oauth_state")
    response.delete_cookie("github_user_id")
    return response


def github_headers(access_token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _frontend_url(kind: str) -> str:
    frontend_url = os.getenv("FRONTEND_URL", "http://127.0.0.1:5173")
    env_name = (
        "FRONTEND_AUTH_SUCCESS_URL"
        if kind == "success"
        else "FRONTEND_AUTH_ERROR_URL"
    )
    return os.getenv(env_name, frontend_url)


def _with_query(url: str, params: dict[str, str]) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query.update(params)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )

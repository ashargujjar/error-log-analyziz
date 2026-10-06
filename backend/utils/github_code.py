from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlparse

import httpx


GITHUB_API_URL = "https://api.github.com"


def parse_repository_url(repository_url: str | None) -> tuple[str, str] | None:
    if not repository_url:
        return None

    parsed = urlparse(repository_url)
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        return None

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return None

    owner = parts[0]
    repository = parts[1].removesuffix(".git")
    if not owner or not repository:
        return None

    return owner, repository


def fetch_github_file(
    file_path: str,
    repository_url: str | None,
    repository_ref: str | None = None,
    access_token: str | None = None,
) -> dict[str, Any]:
    repository = parse_repository_url(repository_url)
    if repository is None:
        return {
            "available": False,
            "reason": "A valid GitHub repository URL was not found.",
        }

    owner, repo = repository
    encoded_path = quote(file_path.lstrip("/"), safe="/")
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{encoded_path}"
    params = {"ref": repository_ref} if repository_ref else None
    headers = {
        "Accept": "application/vnd.github.raw+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(url, params=params, headers=headers)
    except httpx.HTTPError as exc:
        return {
            "available": False,
            "reason": f"GitHub source request failed: {exc}",
        }

    if response.status_code >= 400:
        return {
            "available": False,
            "reason": (
                f"GitHub source request returned HTTP {response.status_code}. "
                "The repository, file, ref, or token may be unavailable."
            ),
        }

    return {
        "available": True,
        "repository": f"{owner}/{repo}",
        "path": file_path,
        "ref": repository_ref,
        "content": response.text[:20000],
    }

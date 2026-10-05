from typing import Any


async def receive_error(
    payload: dict[str, Any],
) -> dict[str, Any]:
    github_id = payload.pop("github_id", None)
    name = payload.pop("name", None)

    return {
        "message": "Error received.",
        "github_id": github_id,
        "name": name,
        "error": payload,
    }

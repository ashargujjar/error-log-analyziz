from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from models.models import APIKey
from schema.schema import APIKeyCreateRequest, APIKeyCreatedResponse, APIKeyHistoryItem


def verified_user_id(request: Request) -> str:
    github_id = getattr(request.state, "github_id", None)
    if not github_id:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return github_id


async def create_api_key(
    payload: APIKeyCreateRequest,
    request: Request,
) -> APIKeyCreatedResponse:
    user_id = verified_user_id(request)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="API key name is required.")

    return await APIKey().create(user_id, name)


async def list_api_keys(
    request: Request,
) -> list[APIKeyHistoryItem]:
    return await APIKey().list_for_user(verified_user_id(request))


async def revoke_api_key(key_id: str, request: Request) -> JSONResponse:
    revoked = await APIKey().revoke_for_user(
        verified_user_id(request),
        key_id,
    )
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found.")

    return JSONResponse({"message": "API key deleted."})

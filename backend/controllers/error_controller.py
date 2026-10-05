import json
from typing import Any

from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool

from models.models import ErrorLog
from utils.dataExtraction import extractErrorData


async def receive_error(
    payload: dict[str, Any],
) -> dict[str, Any]:
    github_id = payload.pop("github_id", None)
    name = payload.pop("name", None)

    if not github_id:
        raise HTTPException(status_code=401, detail="A valid API key is required.")

    try:
        structured_error = await run_in_threadpool(
            extractErrorData,
            json.dumps(payload, ensure_ascii=False),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to extract structured error data.",
        ) from exc

    structured_error_data = structured_error.model_dump()
    error_id = await ErrorLog().create(github_id, structured_error_data)

    return {
        "message": "Error received.",
        "error_id": error_id,
        "github_id": github_id,
        "name": name,
        "error": structured_error_data,
    }

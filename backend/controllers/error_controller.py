import json
from typing import Any

from fastapi import BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from llm.langgraph import run_error_workflow
from models.error_log_model import ErrorLog
from models.user_model import User
from utils.dataExtraction import extractErrorData


async def process_error(error_id: str) -> None:
    error_log = ErrorLog()
    record = await error_log.get_by_id(error_id)
    if record is None or not await error_log.mark_processing(error_id):
        return

    try:
        raw_log = record.get("payload", "")
        if not isinstance(raw_log, str):
            raw_log = json.dumps(raw_log, ensure_ascii=False)

        structured_error = await run_in_threadpool(
            extractErrorData,
            raw_log,
        )
        github_access_token = await User().get_github_access_token(
            record["github_id"]
        )
        workflow_result = await run_in_threadpool(
            run_error_workflow,
            structured_error.model_dump(),
            github_access_token,
        )

        await error_log.mark_processed(
            error_id,
            workflow_result["structured_error"],
            workflow_result["analysis"],
        )
    except Exception as exc:
        await error_log.mark_failed(error_id, str(exc))


async def receive_error(
    request: Request,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    github_id = getattr(request.state, "github_id", None)
    name = getattr(request.state, "api_key_name", None)

    if not github_id:
        raise HTTPException(status_code=401, detail="A valid API key is required.")

    raw_log = (await request.body()).decode("utf-8", errors="replace")
    if not raw_log.strip():
        raise HTTPException(status_code=400, detail="Request body must contain an error log.")

    content_type = request.headers.get("content-type", "text/plain")
    error_id = await ErrorLog().create(
        github_id,
        raw_log,
        name,
        content_type,
    )
    background_tasks.add_task(process_error, error_id)

    return JSONResponse(
        status_code=202,
        content={
            "message": "Error received and queued for processing.",
            "error_id": error_id,
            "github_id": github_id,
            "name": name,
            "status": "pending",
        },
    )


async def get_error_status(
    error_id: str,
    request: Request,
) -> dict[str, Any]:
    github_id = getattr(request.state, "github_id", None)
    if not github_id:
        raise HTTPException(status_code=401, detail="A valid API key is required.")

    status = await ErrorLog().get_status(error_id, github_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Error log not found.")

    return status


async def list_errors(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    github_id = getattr(request.state, "github_id", None)
    if not github_id:
        raise HTTPException(status_code=401, detail="Authentication required.")

    return await ErrorLog().list_for_user(github_id, limit)


async def delete_error(
    error_id: str,
    request: Request,
) -> dict[str, str]:
    github_id = getattr(request.state, "github_id", None)
    if not github_id:
        raise HTTPException(status_code=401, detail="Authentication required.")

    deleted = await ErrorLog().delete_for_user(error_id, github_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Error log not found.")

    return {"message": "Error log deleted.", "error_id": error_id}


async def reprocess_error(
    error_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    github_id = getattr(request.state, "github_id", None)
    if not github_id:
        raise HTTPException(status_code=401, detail="Authentication required.")

    error_log = ErrorLog()
    existing = await error_log.get_status(error_id, github_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Error log not found.")
    if existing.get("status") != "failed":
        raise HTTPException(
            status_code=409,
            detail="Only failed error logs can be re-executed.",
        )

    queued = await error_log.queue_failed_for_reprocess(error_id, github_id)
    if queued is None:
        raise HTTPException(
            status_code=409,
            detail="Error log could not be queued for reprocessing.",
        )

    background_tasks.add_task(process_error, error_id)
    return queued

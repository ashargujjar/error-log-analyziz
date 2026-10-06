from fastapi import APIRouter

from controllers.error_controller import (
    approve_error_issue,
    delete_error,
    get_error_status,
    list_errors,
    receive_error,
    reprocess_error,
)


router = APIRouter(prefix="/errors", tags=["errors"])


router.add_api_route("", receive_error, methods=["POST"])
router.add_api_route("", list_errors, methods=["GET"])
router.add_api_route("/{error_id}/approve", approve_error_issue, methods=["POST"])
router.add_api_route("/{error_id}/reprocess", reprocess_error, methods=["POST"])
router.add_api_route("/{error_id}", get_error_status, methods=["GET"])
router.add_api_route("/{error_id}", delete_error, methods=["DELETE"])

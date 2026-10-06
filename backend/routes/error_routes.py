from fastapi import APIRouter

from controllers.error_controller import (
    get_error_status,
    list_errors,
    receive_error,
)


router = APIRouter(prefix="/errors", tags=["errors"])


router.add_api_route("", receive_error, methods=["POST"])
router.add_api_route("", list_errors, methods=["GET"])
router.add_api_route("/{error_id}", get_error_status, methods=["GET"])

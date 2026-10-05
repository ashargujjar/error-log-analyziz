from fastapi import APIRouter

from controllers.error_controller import receive_error


router = APIRouter(prefix="/errors", tags=["errors"])


router.add_api_route("", receive_error, methods=["POST"])

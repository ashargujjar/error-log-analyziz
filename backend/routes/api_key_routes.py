from fastapi import APIRouter

from controllers.api_key_controller import (
    create_api_key,
    list_api_keys,
    revoke_api_key,
)


router = APIRouter(prefix="/api-keys", tags=["api-keys"])


router.add_api_route("", create_api_key, methods=["POST"])
router.add_api_route("", list_api_keys, methods=["GET"])
router.add_api_route("/{key_id}", revoke_api_key, methods=["DELETE"])

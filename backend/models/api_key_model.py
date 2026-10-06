from datetime import datetime
import hashlib
import secrets

from db.db import database
from schema.schema import APIKeyCreatedResponse, APIKeyHistoryItem


class APIKey:
    def __init__(self, db=database):
        self.collection = db["api_keys"]

    async def find_user_by_key(self, raw_key: str) -> dict | None:
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        return await self.collection.find_one(
            {
                "key_hash": key_hash,
                "revoked_at": None,
            },
            {
                "_id": 0,
                "github_id": 1,
                "name": 1,
            },
        )

    async def create(self, github_id: str, name: str) -> APIKeyCreatedResponse:
        now = datetime.utcnow()
        raw_key = f"ela_{secrets.token_urlsafe(32)}"
        key_id = secrets.token_urlsafe(12)

        document = {
            "key_id": key_id,
            "github_id": github_id,
            "name": name.strip(),
            "prefix": raw_key[:12],
            "key_hash": hashlib.sha256(raw_key.encode("utf-8")).hexdigest(),
            "created_at": now,
            "revoked_at": None,
        }
        await self.collection.insert_one(document)

        return APIKeyCreatedResponse(
            id=key_id,
            name=document["name"],
            prefix=document["prefix"],
            created_at=now,
            revoked_at=None,
            key=raw_key,
        )

    async def list_for_user(self, github_id: str) -> list[APIKeyHistoryItem]:
        cursor = self.collection.find(
            {"github_id": github_id},
            {
                "_id": 0,
                "key_id": 1,
                "name": 1,
                "prefix": 1,
                "created_at": 1,
                "revoked_at": 1,
            },
        ).sort("created_at", -1)

        return [
            APIKeyHistoryItem(
                id=document["key_id"],
                name=document["name"],
                prefix=document["prefix"],
                created_at=document["created_at"],
                revoked_at=document.get("revoked_at"),
            )
            async for document in cursor
        ]

    async def revoke_for_user(self, github_id: str, key_id: str) -> bool:
        result = await self.collection.update_one(
            {
                "github_id": github_id,
                "key_id": key_id,
                "revoked_at": None,
            },
            {"$set": {"revoked_at": datetime.utcnow()}},
        )
        return result.modified_count > 0

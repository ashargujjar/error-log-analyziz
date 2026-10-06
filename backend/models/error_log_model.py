from datetime import datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from db.db import database


class ErrorLog:
    def __init__(self, db=database):
        self.collection = db["errors"]

    async def create(
        self,
        github_id: str,
        payload: str,
        source_name: str | None = None,
        content_type: str = "text/plain",
    ) -> str:
        now = datetime.utcnow()
        result = await self.collection.insert_one(
            {
                "github_id": github_id,
                "source_name": source_name,
                "payload": payload,
                "payload_content_type": content_type,
                "error": None,
                "analysis": None,
                "incident": None,
                "approval": "pending",
                "status": "pending",
                "error_message": None,
                "attempts": 0,
                "created_at": now,
                "updated_at": now,
                "processing_started_at": None,
                "processed_at": None,
            }
        )
        return str(result.inserted_id)

    async def get_by_id(self, error_id: str) -> dict[str, Any] | None:
        try:
            object_id = ObjectId(error_id)
        except (InvalidId, TypeError):
            return None

        return await self.collection.find_one({"_id": object_id})

    async def mark_processing(self, error_id: str) -> bool:
        record = await self.get_by_id(error_id)
        if record is None or record.get("status") not in {"pending", "failed"}:
            return False

        now = datetime.utcnow()
        result = await self.collection.update_one(
            {
                "_id": record["_id"],
                "status": record.get("status"),
            },
            {
                "$set": {
                    "status": "processing",
                    "updated_at": now,
                    "processing_started_at": now,
                    "error_message": None,
                },
                "$inc": {"attempts": 1},
            },
        )
        return result.modified_count == 1

    async def mark_processed(
        self,
        error_id: str,
        structured_error: dict[str, Any],
        analysis: dict[str, Any] | None = None,
    ) -> bool:
        try:
            object_id = ObjectId(error_id)
        except (InvalidId, TypeError):
            return False

        now = datetime.utcnow()
        incident = None
        if analysis:
            incident = analysis.get("aggregator")
            if isinstance(incident, dict):
                incident = {**incident, "approval": "pending"}

        result = await self.collection.update_one(
            {"_id": object_id, "status": "processing"},
            {
                "$set": {
                    "status": "processed",
                    "error": structured_error,
                    "analysis": analysis,
                    "incident": incident,
                    "approval": "pending",
                    "error_message": None,
                    "updated_at": now,
                    "processed_at": now,
                }
            },
        )
        return result.modified_count == 1

    async def mark_failed(
        self,
        error_id: str,
        error_message: str,
    ) -> bool:
        try:
            object_id = ObjectId(error_id)
        except (InvalidId, TypeError):
            return False

        now = datetime.utcnow()
        result = await self.collection.update_one(
            {"_id": object_id, "status": "processing"},
            {
                "$set": {
                    "status": "failed",
                    "error_message": error_message[:1000],
                    "updated_at": now,
                }
            },
        )
        return result.modified_count == 1

    async def get_status(
        self,
        error_id: str,
        github_id: str,
    ) -> dict[str, Any] | None:
        try:
            object_id = ObjectId(error_id)
        except (InvalidId, TypeError):
            return None

        document = await self.collection.find_one(
            {"_id": object_id, "github_id": github_id},
            {
                "_id": 1,
                "status": 1,
                "source_name": 1,
                "payload": 1,
                "payload_content_type": 1,
                "error": 1,
                "analysis": 1,
                "incident": 1,
                "approval": 1,
                "error_message": 1,
                "attempts": 1,
                "created_at": 1,
                "updated_at": 1,
                "processing_started_at": 1,
                "processed_at": 1,
            },
        )
        if document is None:
            return None

        document["error_id"] = str(document.pop("_id"))
        return document

    async def delete_for_user(
        self,
        error_id: str,
        github_id: str,
    ) -> bool:
        try:
            object_id = ObjectId(error_id)
        except (InvalidId, TypeError):
            return False

        result = await self.collection.delete_one(
            {"_id": object_id, "github_id": github_id}
        )
        return result.deleted_count == 1

    async def queue_failed_for_reprocess(
        self,
        error_id: str,
        github_id: str,
    ) -> dict[str, Any] | None:
        try:
            object_id = ObjectId(error_id)
        except (InvalidId, TypeError):
            return None

        now = datetime.utcnow()
        result = await self.collection.update_one(
            {
                "_id": object_id,
                "github_id": github_id,
                "status": "failed",
            },
            {
                "$set": {
                    "status": "pending",
                    "error": None,
                    "analysis": None,
                    "incident": None,
                    "approval": "pending",
                    "error_message": None,
                    "updated_at": now,
                    "processing_started_at": None,
                    "processed_at": None,
                }
            },
        )
        if result.modified_count != 1:
            return None

        return await self.get_status(error_id, github_id)

    async def list_for_user(
        self,
        github_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        cursor = (
            self.collection.find(
                {"github_id": github_id},
                {
                    "_id": 1,
                    "source_name": 1,
                    "payload": 1,
                    "payload_content_type": 1,
                    "error": 1,
                    "analysis": 1,
                    "incident": 1,
                    "approval": 1,
                    "status": 1,
                    "error_message": 1,
                    "attempts": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "processing_started_at": 1,
                    "processed_at": 1,
                },
            )
            .sort("created_at", -1)
            .limit(limit)
        )

        records = []
        async for document in cursor:
            document["error_id"] = str(document.pop("_id"))
            records.append(document)
        return records

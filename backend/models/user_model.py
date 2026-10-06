from datetime import datetime, timedelta
import hashlib
import secrets

from db.db import database
from schema.schema import GitHubOAuthAccount, UserSchema
from utils.github_auth_utils import decrypt_token


class User:
    def __init__(self, db=database):
        self.users_collection = db["users"]
        self.github_accounts_collection = db["github_oauth_accounts"]
        self.sessions_collection = db["auth_sessions"]

    async def create(
        self,
        user: UserSchema,
        github_account: GitHubOAuthAccount,
    ) -> dict[str, str]:
        user_data = user.model_dump()
        user_result = await self.users_collection.insert_one(user_data)

        github_account_data = github_account.model_dump()
        github_account_data["user_id"] = str(user_result.inserted_id)
        github_account_data["created_at"] = datetime.utcnow()
        github_account_data["updated_at"] = datetime.utcnow()
        github_account_result = await self.github_accounts_collection.insert_one(
            github_account_data
        )

        return {
            "user_id": str(user_result.inserted_id),
            "github_account_id": str(github_account_result.inserted_id),
        }

    async def save_github_oauth_user(
        self,
        user: UserSchema,
        github_account: GitHubOAuthAccount,
    ) -> dict[str, str]:
        existing_user = await self.users_collection.find_one(
            {"github_id": user.github_id}
        )

        if existing_user is None:
            return await self.create(user, github_account)

        now = datetime.utcnow()
        user_id = str(existing_user["_id"])
        user_data = user.model_dump()
        user_data.pop("created_at", None)
        user_data["updated_at"] = now

        await self.users_collection.update_one(
            {"_id": existing_user["_id"]},
            {"$set": user_data},
        )

        github_account_data = github_account.model_dump(exclude={"created_at"})
        github_account_data["user_id"] = user_id
        github_account_data["updated_at"] = now

        github_account_result = await self.github_accounts_collection.update_one(
            {"user_id": user_id},
            {
                "$set": github_account_data,
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

        github_account_id = github_account_result.upserted_id
        if github_account_id is None:
            existing_account = await self.github_accounts_collection.find_one(
                {"user_id": user_id}
            )
            github_account_id = existing_account["_id"]

        return {
            "user_id": user_id,
            "github_account_id": str(github_account_id),
        }

    async def sign_out(self, github_id: str) -> bool:
        user = await self.users_collection.find_one({"github_id": github_id})
        if user is None:
            return False

        result = await self.github_accounts_collection.delete_one(
            {"user_id": str(user["_id"])}
        )
        return result.deleted_count > 0

    async def create_session(self, github_id: str) -> str:
        session_token = secrets.token_urlsafe(48)
        now = datetime.utcnow()

        await self.sessions_collection.delete_many(
            {"github_id": github_id, "expires_at": {"$lte": now}}
        )
        await self.sessions_collection.insert_one(
            {
                "session_hash": hashlib.sha256(
                    session_token.encode("utf-8")
                ).hexdigest(),
                "github_id": github_id,
                "created_at": now,
                "expires_at": now + timedelta(days=30),
            }
        )
        return session_token

    async def get_user_for_session(self, session_token: str | None) -> dict | None:
        if not session_token:
            return None

        session_hash = hashlib.sha256(
            session_token.encode("utf-8")
        ).hexdigest()
        session = await self.sessions_collection.find_one(
            {
                "session_hash": session_hash,
                "expires_at": {"$gt": datetime.utcnow()},
            }
        )
        if session is None:
            return None

        return await self.users_collection.find_one(
            {"github_id": session["github_id"]}
        )

    async def delete_session(self, session_token: str | None) -> None:
        if not session_token:
            return

        session_hash = hashlib.sha256(
            session_token.encode("utf-8")
        ).hexdigest()
        await self.sessions_collection.delete_one({"session_hash": session_hash})

    async def get_github_access_token(self, github_id: str) -> str | None:
        user = await self.users_collection.find_one(
            {"github_id": github_id},
            {"_id": 1},
        )
        if user is None:
            return None

        account = await self.github_accounts_collection.find_one(
            {"user_id": str(user["_id"])},
            {"access_token_encrypted": 1},
        )
        if not account or not account.get("access_token_encrypted"):
            return None

        return decrypt_token(account["access_token_encrypted"])

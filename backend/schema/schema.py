from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserSchema(BaseModel):
    github_id: str
    username: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GitHubOAuthAccount(BaseModel):
    user_id: Optional[str] = None
    access_token_encrypted: str
    refresh_token_encrypted: Optional[str] = None
    token_type: str = "bearer"
    scope: Optional[str] = None
    access_token_expires_at: Optional[datetime] = None
    refresh_token_expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class APIKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class APIKeyHistoryItem(BaseModel):
    id: str
    name: str
    prefix: str
    created_at: datetime
    revoked_at: Optional[datetime] = None


class APIKeyCreatedResponse(APIKeyHistoryItem):
    key: str

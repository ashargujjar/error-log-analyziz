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


class ErrorFileEvidence(BaseModel):
    filePath: str = Field(
        description="Path or name of the source file where the error occurred.",
    )
    lineNumber: Optional[int] = Field(
        default=None,
        ge=1,
        description="Source-code line number where the error was encountered.",
    )
    lineSource: Optional[str] = Field(
        default=None,
        description="Source-code line containing or indicating the error.",
    )


# Error information extracted from an error description.
class errorStructureData(BaseModel):
    errorFiles: Optional[list[ErrorFileEvidence]] = Field(
        default=None,
        description="Source files and line-level evidence associated with the error.",
    )
    errorType: str = Field(
        description="Type or category of the error.",
    )
    errorMessages: Optional[str] = Field(
        default=None,
        description="Original error message or messages.",
    )
    functionClassName: Optional[str] = Field(
        default=None,
        description="Function, method, or class where the error occurred.",
    )
    description: str = Field(
        description="Clear description of the error extracted from the input.",
    )

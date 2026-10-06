from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


ERROR_CATEGORIES = (
    "code_error",
    "database_error",
    "network_error",
    "configuration_error",
    "authentication_error",
    "rate_limit_error",
    "dependency_error",
    "infrastructure_error",
    "external_api_error",
    "unknown",
)

ErrorCategory = Literal[
    "code_error",
    "database_error",
    "network_error",
    "configuration_error",
    "authentication_error",
    "rate_limit_error",
    "dependency_error",
    "infrastructure_error",
    "external_api_error",
    "unknown",
]


def normalize_error_category(value: object) -> ErrorCategory:
    if not isinstance(value, str):
        return "unknown"

    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "code": "code_error",
        "database": "database_error",
        "db_error": "database_error",
        "network": "network_error",
        "configuration": "configuration_error",
        "config_error": "configuration_error",
        "authentication": "authentication_error",
        "auth_error": "authentication_error",
        "rate_limit": "rate_limit_error",
        "dependency": "dependency_error",
        "infrastructure": "infrastructure_error",
        "external_api": "external_api_error",
        "general": "unknown",
        "general_error": "unknown",
        "other": "unknown",
    }
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in ERROR_CATEGORIES else "unknown"


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


class GitHubRepositoryItem(BaseModel):
    full_name: str
    private: bool = False
    html_url: str


class GitHubIssueApprovalRequest(BaseModel):
    repo: str = Field(
        min_length=3,
        max_length=200,
        pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$",
        description="Repository full name in owner/repo format.",
    )


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
    repositoryUrl: Optional[str] = Field(
        default=None,
        description="GitHub repository URL found in the error log, if present.",
    )
    repositoryRef: Optional[str] = Field(
        default=None,
        description="Branch, tag, or commit SHA found in the error log, if present.",
    )
    errorFiles: Optional[list[ErrorFileEvidence]] = Field(
        default=None,
        description="Source files and line-level evidence associated with the error.",
    )
    errorType: ErrorCategory = Field(
        description=(
            "Exactly one category: code_error, database_error, network_error, "
            "configuration_error, authentication_error, rate_limit_error, "
            "dependency_error, infrastructure_error, external_api_error, or unknown."
        ),
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

    @field_validator("errorType", mode="before")
    @classmethod
    def normalize_error_type(cls, value: object) -> ErrorCategory:
        return normalize_error_category(value)

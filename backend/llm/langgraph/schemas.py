from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


AnalyzerName = Literal[
    "code_analyzer",
    "database_analyzer",
    "infrastructure_analyzer",
    "external_api_analyzer",
]

ANALYZER_NAMES = (
    "code_analyzer",
    "database_analyzer",
    "infrastructure_analyzer",
    "external_api_analyzer",
)


class SupervisorDecision(BaseModel):
    selected_analyzers: list[AnalyzerName] = Field(
        min_length=1,
        max_length=4,
        description=(
            "The analyzer nodes that should run in parallel. Select only "
            "analyzers relevant to the structured error."
        ),
    )
    reason: str = Field(
        min_length=1,
        description="Short explanation for the selected analyzer nodes.",
    )

    @field_validator("selected_analyzers")
    @classmethod
    def remove_duplicates(
        cls,
        analyzers: list[AnalyzerName],
    ) -> list[AnalyzerName]:
        return list(dict.fromkeys(analyzers))


class AnalyzerFinding(BaseModel):
    relevant: bool = Field(
        description="Whether this analyzer found evidence relevant to its domain.",
    )
    confidence: float = Field(
        ge=0,
        le=1,
        description="Confidence in this analyzer's finding, from 0 to 1.",
    )
    finding: str = Field(
        description="The analyzer's concise finding.",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Evidence from the structured error supporting the finding.",
    )
    recommended_action: Optional[str] = Field(
        default=None,
        description="Recommended next action when this analyzer is relevant.",
    )
    source_context_available: bool = Field(
        default=False,
        description="Whether repository source code was available to the analyzer.",
    )
    source_context_files: list[str] = Field(
        default_factory=list,
        description="Repository files loaded for analysis.",
    )
    traces_to_check: list[str] = Field(
        default_factory=list,
        description="Specific code traces, files, or functions to inspect.",
    )


class DatabaseAnalyzerFinding(AnalyzerFinding):
    database_type: Literal[
        "mongodb",
        "postgresql",
        "mysql",
        "redis",
        "sqlite",
        "dynamodb",
        "oracle",
        "unknown",
    ] = Field(
        default="unknown",
        description="Database involved in the failure, if identifiable.",
    )
    failure_type: Literal[
        "connection_failure",
        "query_error",
        "schema_error",
        "migration_error",
        "transaction_error",
        "index_error",
        "timeout_error",
        "authentication_error",
        "availability_error",
        "unknown",
    ] = Field(
        default="unknown",
        description="Specific database failure type.",
    )


class InfrastructureAnalyzerFinding(AnalyzerFinding):
    infrastructure_type: Literal[
        "server",
        "container",
        "kubernetes",
        "cloud",
        "load_balancer",
        "deployment",
        "host",
        "environment",
        "unknown",
    ] = Field(
        default="unknown",
        description="Infrastructure area involved in the failure.",
    )
    failure_type: Literal[
        "crash",
        "resource_exhaustion",
        "disk_full",
        "deployment_failure",
        "availability_failure",
        "service_restart",
        "network_failure",
        "configuration_failure",
        "health_check_failure",
        "unknown",
    ] = Field(
        default="unknown",
        description="Specific infrastructure failure type.",
    )


class ExternalAPIAnalyzerFinding(AnalyzerFinding):
    provider: Literal[
        "github",
        "stripe",
        "aws",
        "openai",
        "deepseek",
        "unknown",
    ] = Field(
        default="unknown",
        description="External provider involved in the failure.",
    )
    failure_type: Literal[
        "authentication_failure",
        "authorization_failure",
        "not_found",
        "rate_limit",
        "server_error",
        "timeout",
        "outage",
        "webhook_failure",
        "network_failure",
        "invalid_request",
        "unknown",
    ] = Field(
        default="unknown",
        description="Specific external API failure type.",
    )
    http_status: Optional[int] = Field(
        default=None,
        ge=100,
        le=599,
        description="HTTP status code found in the evidence, if available.",
    )


class AggregatedAnalysis(BaseModel):
    title: str = Field(
        description="Short title for the incident or error.",
    )
    severity: Literal["critical", "high", "medium", "low"] = Field(
        description="Severity of the issue based on impact and risk.",
    )
    ai_confidence_score: float = Field(
        ge=0,
        le=1,
        description="AI confidence in the final finding, from 0 to 1.",
    )
    approval: Literal["pending", "approved"] = Field(
        default="pending",
        description="Human approval state. New analyses must default to pending.",
    )
    primary_analyzer: Literal[
        "code_analyzer",
        "database_analyzer",
        "infrastructure_analyzer",
        "external_api_analyzer",
        "none",
    ] = Field(
        description="The analyzer with the strongest relevant finding, or none.",
    )
    description: str = Field(
        description="Clear description of the final finding.",
    )
    impact: str = Field(
        description="What this error can break or degrade for users or systems.",
    )
    risks: list[str] = Field(
        default_factory=list,
        description="Risks if this issue is ignored.",
    )
    recommendation: str = Field(
        description="Recommended fix or next action for an engineer.",
    )
    traces_to_check: list[str] = Field(
        default_factory=list,
        description="Specific files, functions, services, messages, or traces to inspect.",
    )

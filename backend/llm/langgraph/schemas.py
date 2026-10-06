from typing import Literal, Optional

from pydantic import BaseModel, Field


AnalyzerName = Literal[
    "code_analyzer",
    "database_analyzer",
    "infrastructure_analyzer",
    "external_api_analyzer",
]


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


class AggregatedAnalysis(BaseModel):
    primary_analyzer: Literal[
        "code_analyzer",
        "database_analyzer",
        "infrastructure_analyzer",
        "external_api_analyzer",
        "none",
    ] = Field(
        description="The analyzer with the strongest relevant finding, or none.",
    )
    summary: str = Field(
        description="A concise final summary of what the error is encountering.",
    )
    root_cause: str = Field(
        description="The most likely root cause based only on the available evidence.",
    )
    recommended_action: str = Field(
        description="The clearest recommended next action for an engineer.",
    )

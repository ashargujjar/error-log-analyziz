from typing import Any, TypedDict


class ErrorWorkflowState(TypedDict, total=False):
    structured_error: dict[str, Any]
    code_analysis: dict[str, Any]
    database_analysis: dict[str, Any]
    infrastructure_analysis: dict[str, Any]
    external_api_analysis: dict[str, Any]
    aggregated_analysis: dict[str, Any]

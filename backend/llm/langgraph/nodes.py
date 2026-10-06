import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek

from llm.langgraph.schemas import (
    ANALYZER_NAMES,
    AggregatedAnalysis,
    AnalyzerFinding,
    SupervisorDecision,
)
from llm.langgraph.state import ErrorWorkflowState


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


@lru_cache(maxsize=1)
def _get_analysis_llm():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured.")

    return ChatDeepSeek(
        model="deepseek-chat",
        api_key=api_key,
        temperature=0,
    )


def _fallback_supervisor_decision(
    structured_error: dict[str, Any],
) -> SupervisorDecision:
    error_type = structured_error.get("errorType")
    selected = {
        "code_error": ["code_analyzer"],
        "database_error": ["database_analyzer"],
        "infrastructure_error": ["infrastructure_analyzer"],
        "external_api_error": ["external_api_analyzer"],
        "network_error": ["infrastructure_analyzer"],
        "configuration_error": [
            "code_analyzer",
            "infrastructure_analyzer",
        ],
        "authentication_error": [
            "external_api_analyzer",
            "infrastructure_analyzer",
        ],
        "rate_limit_error": ["external_api_analyzer"],
        "dependency_error": ["code_analyzer"],
        "unknown": list(ANALYZER_NAMES),
    }.get(error_type, ["code_analyzer"])

    return SupervisorDecision(
        selected_analyzers=selected,
        reason=(
            "Fallback routing selected analyzers from the structured error "
            f"category: {error_type or 'unknown'}."
        ),
    )


def supervisor_router_node(state: ErrorWorkflowState) -> dict[str, Any]:
    structured_error = state["structured_error"]
    try:
        supervisor = _get_analysis_llm().with_structured_output(
            SupervisorDecision
        )
        decision = supervisor.invoke(
            [
                (
                    "system",
                    (
                        "You are the supervisor router for an error-analysis "
                        "workflow. The raw log has already been converted into "
                        "structured_error. Select only the analyzer nodes that "
                        "need to run. The selected nodes will run in parallel.\n\n"
                        "Available analyzers:\n"
                        "- code_analyzer: application bugs, exceptions, stack "
                        "traces, source files, functions, and code logic\n"
                        "- database_analyzer: database connections, queries, "
                        "schemas, transactions, indexes, and storage\n"
                        "- infrastructure_analyzer: servers, containers, hosts, "
                        "deployments, cloud resources, and capacity\n"
                        "- external_api_analyzer: third-party APIs, HTTP "
                        "responses, credentials, quotas, and integrations\n\n"
                        "Select the smallest set that can explain the error. "
                        "Do not select all analyzers by default. Select multiple "
                        "only when the structured evidence clearly spans those "
                        "domains. Return a short routing reason."
                    ),
                ),
                (
                    "user",
                    "Structured error:\n"
                    + json.dumps(structured_error, ensure_ascii=False),
                ),
            ]
        )
    except Exception:
        decision = _fallback_supervisor_decision(structured_error)

    return {
        "selected_analyzers": decision.selected_analyzers,
        "supervisor_reason": decision.reason,
    }


def route_selected_analyzers(state: ErrorWorkflowState) -> list[Any]:
    from langgraph.types import Send

    return [
        Send(
            analyzer_name,
            {
                "structured_error": state["structured_error"],
                "selected_analyzers": state["selected_analyzers"],
                "supervisor_reason": state["supervisor_reason"],
            },
        )
        for analyzer_name in state["selected_analyzers"]
    ]


def _run_analyzer(
    analyzer_name: str,
    specialty: str,
    structured_error: dict[str, Any],
) -> dict[str, Any]:
    try:
        analyzer = _get_analysis_llm().with_structured_output(AnalyzerFinding)
        result = analyzer.invoke(
            [
                (
                    "system",
                    (
                        f"You are the {analyzer_name}. Analyze only the "
                        f"structured error provided below. Your specialty is: "
                        f"{specialty}\n\n"
                        "Decide whether your specialty is relevant. Do not "
                        "invent raw log lines, files, services, or evidence. "
                        "If your specialty is not relevant, set relevant to "
                        "false, confidence to 0, and explain why briefly."
                    ),
                ),
                (
                    "user",
                    "Structured error:\n"
                    + json.dumps(structured_error, ensure_ascii=False),
                ),
            ]
        )
        return result.model_dump()
    except Exception as exc:
        return AnalyzerFinding(
            relevant=False,
            confidence=0,
            finding=f"{analyzer_name} could not complete: {exc}",
            evidence=[],
            recommended_action=None,
        ).model_dump()


def code_analyzer_node(state: ErrorWorkflowState) -> dict[str, Any]:
    return {
        "code_analysis": _run_analyzer(
            "Code Analyzer",
            (
                "application bugs, incorrect logic, exceptions, stack traces, "
                "source files, line numbers, functions, classes, and code fixes"
            ),
            state["structured_error"],
        )
    }


def database_analyzer_node(state: ErrorWorkflowState) -> dict[str, Any]:
    return {
        "database_analysis": _run_analyzer(
            "Database Analyzer",
            (
                "database connections, queries, schemas, transactions, "
                "indexes, data storage, and database availability"
            ),
            state["structured_error"],
        )
    }


def infrastructure_analyzer_node(state: ErrorWorkflowState) -> dict[str, Any]:
    return {
        "infrastructure_analysis": _run_analyzer(
            "Infrastructure Analyzer",
            (
                "servers, containers, hosts, operating systems, deployments, "
                "cloud resources, capacity, and infrastructure availability"
            ),
            state["structured_error"],
        )
    }


def external_api_analyzer_node(state: ErrorWorkflowState) -> dict[str, Any]:
    return {
        "external_api_analysis": _run_analyzer(
            "External API Analyzer",
            (
                "third-party APIs, provider responses, HTTP status codes, "
                "authentication with external services, quotas, and integrations"
            ),
            state["structured_error"],
        )
    }


def aggregator_node(state: ErrorWorkflowState) -> dict[str, Any]:
    findings = {
        analyzer_name: state[
            f"{analyzer_name.replace('_analyzer', '')}_analysis"
        ]
        for analyzer_name in state["selected_analyzers"]
    }
    aggregator = _get_analysis_llm().with_structured_output(AggregatedAnalysis)
    result = aggregator.invoke(
        [
            (
                "system",
                (
                    "You are the final error-analysis aggregator. Combine the "
                    "four analyzer findings into one user-facing incident state "
                    "for saving to the database. Select the strongest relevant "
                    "analyzer, or none if no analyzer has useful evidence. "
                    "Set approval to pending unless a human has explicitly "
                    "approved it. Use only the structured error and analyzer "
                    "findings. Do not invent evidence.\n\n"
                    "Severity rules: critical means outage, data loss, security "
                    "breach, or widespread production failure; high means a major "
                    "feature or integration is broken; medium means degraded or "
                    "limited functionality; low means minor or unclear impact.\n\n"
                    "traces_to_check must be built from evidence in the analyzer "
                    "findings and structured error, such as file paths, functions, "
                    "services, error messages, HTTP statuses, database names, or "
                    "infrastructure resources."
                ),
            ),
            (
                "user",
                (
                    "Structured error:\n"
                    + json.dumps(
                        state["structured_error"],
                        ensure_ascii=False,
                    )
                    + "\n\nAnalyzer findings:\n"
                    + json.dumps(findings, ensure_ascii=False)
                ),
            ),
        ]
    )
    return {"aggregated_analysis": result.model_dump()}

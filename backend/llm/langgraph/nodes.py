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
    DatabaseAnalyzerFinding,
    SupervisorDecision,
)
from llm.langgraph.state import ErrorWorkflowState
from utils.github_code import fetch_github_file


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
                "github_access_token": state.get("github_access_token"),
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


def _code_evidence(
    structured_error: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    error_files = structured_error.get("errorFiles") or []
    files = [
        error_file
        for error_file in error_files
        if isinstance(error_file, dict) and error_file.get("filePath")
    ]
    traces = [
        trace
        for trace in (
            structured_error.get("functionClassName"),
            structured_error.get("errorMessages"),
        )
        if isinstance(trace, str) and trace.strip()
    ]
    return files, traces


def _load_code_context(
    structured_error: dict[str, Any],
    github_access_token: str | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    repository_url = structured_error.get("repositoryUrl")
    repository_ref = structured_error.get("repositoryRef")
    error_files, _ = _code_evidence(structured_error)

    contexts = []
    loaded_files = []
    for error_file in error_files[:3]:
        file_path = error_file["filePath"]
        context = fetch_github_file(
            file_path=file_path,
            repository_url=repository_url,
            repository_ref=repository_ref,
            access_token=github_access_token,
        )
        if context.get("available"):
            contexts.append(
                {
                    "file": file_path,
                    "line": error_file.get("lineNumber"),
                    "content": context.get("content", ""),
                }
            )
            loaded_files.append(file_path)

    return contexts, loaded_files


def _run_code_analyzer(state: ErrorWorkflowState) -> dict[str, Any]:
    structured_error = state["structured_error"]
    error_files, traces = _code_evidence(structured_error)
    has_code_evidence = bool(
        error_files
        or structured_error.get("functionClassName")
        or structured_error.get("errorType")
        in {"code_error", "dependency_error"}
    )

    if not has_code_evidence:
        return AnalyzerFinding(
            relevant=False,
            confidence=0.05,
            finding=(
                "No source-code evidence was found in the structured error, "
                "so a code-level cause cannot be confirmed."
            ),
            evidence=["No file, line, function, class, or code error category."],
            recommended_action=(
                "Capture the stack trace, source file, line number, or function "
                "name before investigating a code defect."
            ),
            traces_to_check=traces,
        ).model_dump()

    contexts, loaded_files = _load_code_context(
        structured_error,
        state.get("github_access_token"),
    )
    source_context = (
        json.dumps(contexts, ensure_ascii=False)
        if contexts
        else "No repository source code was available; use only the evidence below."
    )

    try:
        analyzer = _get_analysis_llm().with_structured_output(AnalyzerFinding)
        result = analyzer.invoke(
            [
                (
                    "system",
                    (
                        "You are the Code Analyzer. Follow this workflow exactly:\n"
                        "1. Check errorType and source-code evidence.\n"
                        "2. Inspect files, lines, functions, classes, and stack traces.\n"
                        "3. Find the most likely code problem.\n"
                        "4. Return a code finding.\n\n"
                        "Analyze only the structured error and optional repository "
                        "source context. Do not invent code, files, line numbers, "
                        "or fixes. If repository source is unavailable, clearly "
                        "say that the finding is based on log evidence only. "
                        "Use traces_to_check for exact files, functions, classes, "
                        "messages, and lines that an engineer should inspect."
                    ),
                ),
                (
                    "user",
                    (
                        "Structured error:\n"
                        + json.dumps(structured_error, ensure_ascii=False)
                        + "\n\nRepository source context:\n"
                        + source_context
                    ),
                ),
            ]
        )
        finding = result.model_dump()
        finding["source_context_available"] = bool(contexts)
        finding["source_context_files"] = loaded_files
        finding["traces_to_check"] = list(
            dict.fromkeys(
                [
                    *finding.get("traces_to_check", []),
                    *[error_file["filePath"] for error_file in error_files],
                    *traces,
                ]
            )
        )
        return AnalyzerFinding(**finding).model_dump()
    except Exception as exc:
        return AnalyzerFinding(
            relevant=True,
            confidence=0.2,
            finding=f"Code analysis could not complete: {exc}",
            evidence=traces,
            recommended_action=(
                "Inspect the listed source files and stack-trace location manually."
            ),
            source_context_available=bool(contexts),
            source_context_files=loaded_files,
            traces_to_check=traces
            + [error_file["filePath"] for error_file in error_files],
        ).model_dump()


def code_analyzer_node(state: ErrorWorkflowState) -> dict[str, Any]:
    return {"code_analysis": _run_code_analyzer(state)}


def _database_evidence(
    structured_error: dict[str, Any],
) -> tuple[bool, str, list[str], list[str]]:
    database_patterns = {
        "mongodb": ("mongodb", "mongo", "mongoserverselectionerror"),
        "postgresql": ("postgresql", "postgres", "psycopg", "asyncpg"),
        "mysql": ("mysql", "mysqldb", "pymysql"),
        "redis": ("redis", "redispy", "redissentinel"),
        "sqlite": ("sqlite", "sqlite3"),
        "dynamodb": ("dynamodb", "boto3"),
        "oracle": ("oracle", "cx_oracle", "oracledb"),
    }
    database_failure_patterns = {
        "connection_failure": (
            "connection refused",
            "could not connect",
            "connection failed",
            "server selection",
            "connection pool",
        ),
        "query_error": (
            "query",
            "sql syntax",
            "syntax error",
            "deadlock",
            "duplicate key",
        ),
        "schema_error": (
            "schema",
            "column does not exist",
            "table does not exist",
            "relation does not exist",
        ),
        "migration_error": ("migration", "migrate", "migration failed"),
        "transaction_error": (
            "transaction",
            "rollback",
            "commit failed",
            "serialization failure",
        ),
        "index_error": ("index", "index missing", "index failed"),
        "timeout_error": ("timeout", "timed out", "statement timeout"),
        "authentication_error": (
            "database authentication",
            "authentication failed",
            "invalid database password",
            "access denied",
        ),
        "availability_error": (
            "database unavailable",
            "database is down",
            "service unavailable",
        ),
    }

    searchable_values = [
        structured_error.get("errorMessages"),
        structured_error.get("description"),
        structured_error.get("functionClassName"),
    ]
    for error_file in structured_error.get("errorFiles") or []:
        if isinstance(error_file, dict):
            searchable_values.extend(
                [
                    error_file.get("filePath"),
                    error_file.get("lineSource"),
                ]
            )

    searchable_text = " ".join(
        value.lower()
        for value in searchable_values
        if isinstance(value, str)
    )
    database_type = "unknown"
    for candidate, patterns in database_patterns.items():
        if any(pattern in searchable_text for pattern in patterns):
            database_type = candidate
            break

    failure_type = "unknown"
    for candidate, patterns in database_failure_patterns.items():
        if any(pattern in searchable_text for pattern in patterns):
            failure_type = candidate
            break

    relevant = structured_error.get("errorType") == "database_error" or (
        database_type != "unknown" or failure_type != "unknown"
    )
    evidence = []
    traces = []
    if structured_error.get("errorType") == "database_error":
        evidence.append("errorType is database_error")
    if database_type != "unknown":
        evidence.append(f"database evidence indicates {database_type}")
    if failure_type != "unknown":
        evidence.append(f"database evidence indicates {failure_type}")

    for value in searchable_values:
        if isinstance(value, str) and value.strip():
            traces.append(value.strip())

    return relevant, database_type, evidence, list(dict.fromkeys(traces))


def _run_database_analyzer(state: ErrorWorkflowState) -> dict[str, Any]:
    structured_error = state["structured_error"]
    relevant, database_type, evidence, traces = _database_evidence(
        structured_error
    )

    if not relevant:
        return DatabaseAnalyzerFinding(
            relevant=False,
            confidence=0.05,
            finding=(
                "No database-related evidence was found in the structured error."
            ),
            evidence=[
                "No database type, database failure message, or database error category."
            ],
            recommended_action=(
                "Capture the database error message, query, database type, "
                "or connection details."
            ),
            traces_to_check=traces,
        ).model_dump()

    try:
        analyzer = _get_analysis_llm().with_structured_output(
            DatabaseAnalyzerFinding
        )
        result = analyzer.invoke(
            [
                (
                    "system",
                    (
                        "You are the Database Analyzer. Follow this workflow:\n"
                        "1. Check database-related evidence.\n"
                        "2. Identify the database and failure type.\n"
                        "3. Analyze connection, query, schema, migration, "
                        "transaction, index, timeout, authentication, or "
                        "availability problems.\n"
                        "4. Return a database finding.\n\n"
                        "You analyze only the structured error. Do not connect "
                        "to a live database, invent queries, credentials, "
                        "schemas, or evidence. Supported database types include "
                        "MongoDB, PostgreSQL, MySQL, Redis, SQLite, DynamoDB, "
                        "and Oracle. Use unknown when the evidence is "
                        "insufficient. Include exact error messages and "
                        "function/file traces in traces_to_check."
                    ),
                ),
                (
                    "user",
                    "Structured error:\n"
                    + json.dumps(structured_error, ensure_ascii=False)
                ),
            ]
        )
        finding = result.model_dump()
        finding["evidence"] = list(
            dict.fromkeys([*evidence, *finding.get("evidence", [])])
        )
        finding["traces_to_check"] = list(
            dict.fromkeys(
                [*traces, *finding.get("traces_to_check", [])]
            )
        )
        if finding.get("database_type") == "unknown" and database_type != "unknown":
            finding["database_type"] = database_type
        return DatabaseAnalyzerFinding(**finding).model_dump()
    except Exception as exc:
        return DatabaseAnalyzerFinding(
            relevant=True,
            confidence=0.2,
            finding=f"Database analysis could not complete: {exc}",
            evidence=evidence,
            recommended_action=(
                "Inspect the database error, connection settings, and availability "
                "using the listed traces."
            ),
            database_type=database_type,
            failure_type="unknown",
            traces_to_check=traces,
        ).model_dump()


def database_analyzer_node(state: ErrorWorkflowState) -> dict[str, Any]:
    return {"database_analysis": _run_database_analyzer(state)}


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
                    "selected analyzer findings into one user-facing incident state "
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

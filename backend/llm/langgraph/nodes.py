import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek

from llm.langgraph.schemas import AggregatedAnalysis, AnalyzerFinding
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
        "code_analyzer": state["code_analysis"],
        "database_analyzer": state["database_analysis"],
        "infrastructure_analyzer": state["infrastructure_analysis"],
        "external_api_analyzer": state["external_api_analysis"],
    }
    aggregator = _get_analysis_llm().with_structured_output(AggregatedAnalysis)
    result = aggregator.invoke(
        [
            (
                "system",
                (
                    "You are the final error-analysis aggregator. Combine the "
                    "four analyzer findings into one clear conclusion. Select "
                    "the strongest relevant analyzer, or none if no analyzer "
                    "has useful evidence. Use only the structured error and "
                    "the analyzer findings. Do not invent evidence."
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

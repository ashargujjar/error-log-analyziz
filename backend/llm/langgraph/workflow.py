from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from llm.langgraph.nodes import (
    aggregator_node,
    code_analyzer_node,
    database_analyzer_node,
    external_api_analyzer_node,
    infrastructure_analyzer_node,
)
from llm.langgraph.state import ErrorWorkflowState


@lru_cache(maxsize=1)
def _get_error_workflow():
    workflow = StateGraph(ErrorWorkflowState)
    workflow.add_node("code_analyzer", code_analyzer_node)
    workflow.add_node("database_analyzer", database_analyzer_node)
    workflow.add_node("infrastructure_analyzer", infrastructure_analyzer_node)
    workflow.add_node("external_api_analyzer", external_api_analyzer_node)
    workflow.add_node("aggregator", aggregator_node)

    workflow.add_edge(START, "code_analyzer")
    workflow.add_edge(START, "database_analyzer")
    workflow.add_edge(START, "infrastructure_analyzer")
    workflow.add_edge(START, "external_api_analyzer")
    workflow.add_edge("code_analyzer", "aggregator")
    workflow.add_edge("database_analyzer", "aggregator")
    workflow.add_edge("infrastructure_analyzer", "aggregator")
    workflow.add_edge("external_api_analyzer", "aggregator")
    workflow.add_edge("aggregator", END)
    return workflow.compile()


def run_error_workflow(structured_error: dict[str, Any]) -> dict[str, Any]:
    result = _get_error_workflow().invoke(
        {"structured_error": structured_error}
    )
    return {
        "structured_error": result.get("structured_error"),
        "analysis": {
            "code_analyzer": result.get("code_analysis"),
            "database_analyzer": result.get("database_analysis"),
            "infrastructure_analyzer": result.get("infrastructure_analysis"),
            "external_api_analyzer": result.get("external_api_analysis"),
            "aggregator": result.get("aggregated_analysis"),
        },
    }

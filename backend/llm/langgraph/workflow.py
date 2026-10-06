from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from llm.langgraph.nodes import (
    aggregator_node,
    code_analyzer_node,
    database_analyzer_node,
    external_api_analyzer_node,
    infrastructure_analyzer_node,
    route_selected_analyzers,
    supervisor_router_node,
)
from llm.langgraph.state import ErrorWorkflowState


@lru_cache(maxsize=1)
def _get_error_workflow():
    workflow = StateGraph(ErrorWorkflowState)
    workflow.add_node("supervisor_router", supervisor_router_node)
    workflow.add_node("code_analyzer", code_analyzer_node)
    workflow.add_node("database_analyzer", database_analyzer_node)
    workflow.add_node("infrastructure_analyzer", infrastructure_analyzer_node)
    workflow.add_node("external_api_analyzer", external_api_analyzer_node)
    workflow.add_node("aggregator", aggregator_node)

    workflow.add_edge(START, "supervisor_router")
    workflow.add_conditional_edges(
        "supervisor_router",
        route_selected_analyzers,
    )
    workflow.add_edge("code_analyzer", "aggregator")
    workflow.add_edge("database_analyzer", "aggregator")
    workflow.add_edge("infrastructure_analyzer", "aggregator")
    workflow.add_edge("external_api_analyzer", "aggregator")
    workflow.add_edge("aggregator", END)
    return workflow.compile()


def run_error_workflow(
    structured_error: dict[str, Any],
    github_access_token: str | None = None,
) -> dict[str, Any]:
    result = _get_error_workflow().invoke(
        {
            "structured_error": structured_error,
            "github_access_token": github_access_token,
        }
    )
    return {
        "structured_error": result.get("structured_error"),
        "analysis": {
            "supervisor_router": {
                "selected_analyzers": result.get("selected_analyzers", []),
                "reason": result.get("supervisor_reason"),
            },
            **{
                analyzer_name: result.get(
                    f"{analyzer_name.replace('_analyzer', '')}_analysis"
                )
                for analyzer_name in result.get("selected_analyzers", [])
            },
            "aggregator": result.get("aggregated_analysis"),
        },
    }

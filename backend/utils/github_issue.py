from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi import HTTPException

from utils.github_auth_utils import github_headers


GITHUB_API_URL = "https://api.github.com"


async def list_issue_repositories(access_token: str) -> list[dict[str, Any]]:
    repositories: list[dict[str, Any]] = []
    page = 1

    async with httpx.AsyncClient(timeout=15) as client:
        while page <= 5:
            response = await client.get(
                f"{GITHUB_API_URL}/user/repos",
                params={
                    "affiliation": "owner,collaborator,organization_member",
                    "sort": "updated",
                    "per_page": 100,
                    "page": page,
                },
                headers=github_headers(access_token),
            )

            if response.status_code in {401, 403}:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "GitHub repository access is not available. Re-login "
                        "after granting repo permission."
                    ),
                )
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=502,
                    detail="Could not load GitHub repositories.",
                )

            batch = response.json()
            if not batch:
                break

            for repository in batch:
                if repository.get("has_issues") is False:
                    continue
                repositories.append(
                    {
                        "full_name": repository["full_name"],
                        "private": bool(repository.get("private")),
                        "html_url": repository.get("html_url"),
                    }
                )

            if len(batch) < 100:
                break
            page += 1

    return repositories


async def create_github_issue(
    access_token: str,
    repo: str,
    title: str,
    body: str,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{GITHUB_API_URL}/repos/{repo}/issues",
            json={
                "title": title[:256],
                "body": body,
            },
            headers=github_headers(access_token),
        )

    if response.status_code in {401, 403}:
        raise HTTPException(
            status_code=403,
            detail=(
                "GitHub issue creation is not allowed for this repository. "
                "Re-login with repo permission or select another repository."
            ),
        )
    if response.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail="GitHub repository not found or issues are not available.",
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail="GitHub issue creation failed.",
        )

    issue = response.json()
    return {
        "repo": repo,
        "number": issue.get("number"),
        "url": issue.get("html_url"),
        "api_url": issue.get("url"),
        "state": issue.get("state"),
    }


def build_issue_title(record: dict[str, Any]) -> str:
    incident = record.get("incident") if isinstance(record.get("incident"), dict) else {}
    structured_error = record.get("error") if isinstance(record.get("error"), dict) else {}

    title = (
        incident.get("title")
        or structured_error.get("errorMessages")
        or structured_error.get("errorType")
        or "Error log analysis"
    )
    return str(title).splitlines()[0][:256]


def build_issue_body(record: dict[str, Any]) -> str:
    incident = record.get("incident") if isinstance(record.get("incident"), dict) else {}
    structured_error = record.get("error") if isinstance(record.get("error"), dict) else {}
    analysis = record.get("analysis") if isinstance(record.get("analysis"), dict) else {}
    payload = record.get("payload") or ""

    sections = [
        "## AI summary",
        str(incident.get("description") or structured_error.get("description") or "No summary available."),
        "",
        "## Severity and confidence",
        f"- Severity: {incident.get('severity', 'unknown')}",
        f"- AI confidence: {incident.get('ai_confidence_score', 'unknown')}",
        f"- Source: {record.get('source_name') or 'unknown'}",
        "",
        "## Impact",
        str(incident.get("impact") or "Not available."),
        "",
        "## Recommendation",
        str(incident.get("recommendation") or "Not available."),
    ]

    risks = incident.get("risks")
    if isinstance(risks, list) and risks:
        sections.extend(["", "## Risks"])
        sections.extend(f"- {risk}" for risk in risks)

    traces = incident.get("traces_to_check")
    if isinstance(traces, list) and traces:
        sections.extend(["", "## Traces to check"])
        sections.extend(f"- `{trace}`" for trace in traces)

    analyzer_sections = _format_analyzer_findings(analysis)
    if analyzer_sections:
        sections.extend(["", "## Analyzer findings", analyzer_sections])

    sections.extend(
        [
            "",
            "## Structured error",
            "```json",
            _json_block(structured_error, 6000),
            "```",
            "",
            "## Raw log",
            "```text",
            str(payload)[:8000],
            "```",
        ]
    )

    return "\n".join(sections)


def _format_analyzer_findings(analysis: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in analysis.items():
        if key in {"aggregator", "supervisor_router"} or not isinstance(value, dict):
            continue

        finding = value.get("finding")
        if not finding:
            continue

        lines.append(f"### {key.replace('_', ' ').title()}")
        lines.append(f"- Relevant: {value.get('relevant', 'unknown')}")
        lines.append(f"- Confidence: {value.get('confidence', 'unknown')}")
        lines.append(f"- Finding: {finding}")
        if value.get("recommended_action"):
            lines.append(f"- Recommended action: {value['recommended_action']}")
        evidence = value.get("evidence")
        if isinstance(evidence, list) and evidence:
            lines.append("- Evidence:")
            lines.extend(f"  - {item}" for item in evidence[:8])
        lines.append("")

    return "\n".join(lines).strip()


def _json_block(value: Any, limit: int) -> str:
    try:
        dumped = json.dumps(value, indent=2, default=str)
    except TypeError:
        dumped = str(value)

    return dumped[:limit]

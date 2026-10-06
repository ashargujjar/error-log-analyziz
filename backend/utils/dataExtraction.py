import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek

from schema.schema import errorStructureData


load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)


@lru_cache(maxsize=1)
def _get_structured_llm():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured.")

    llm = ChatDeepSeek(
        model="deepseek-chat",
        api_key=api_key,
        temperature=0.2,
    )
    return llm.with_structured_output(errorStructureData)


def extractErrorData(
    logs: str,
) -> errorStructureData:
    result = _get_structured_llm().invoke(
        [
            (
                "system",
                (
                    "Analyze the provided error log and return the required "
                    "structured data. Classify the error into exactly one of "
                    "these categories:\n"
                    "- code_error: a bug or incorrect logic in application source code\n"
                    "- database_error: a database query, connection, schema, or storage failure\n"
                    "- network_error: a connection, DNS, socket, timeout, or transport failure\n"
                    "- configuration_error: missing or invalid environment/configuration values\n"
                    "- authentication_error: invalid credentials, tokens, permissions, or access\n"
                    "- rate_limit_error: a request quota or throttling response\n"
                    "- dependency_error: a failure in a package, library, runtime, or internal dependency\n"
                    "- infrastructure_error: a host, container, OS, cloud resource, or deployment failure\n"
                    "- external_api_error: a failure returned by a third-party API or service\n"
                    "- unknown: the evidence is insufficient to identify a category\n"
                    "Use unknown for a general/unclassifiable error. Do not invent "
                    "a category or use general_error. The errorType field must be "
                    "one of the exact category names above. The description field "
                    "must explain the specific error in plain language. If the "
                    "log includes a GitHub repository URL, branch, tag, or commit "
                    "SHA, preserve it in repositoryUrl or repositoryRef. "
                    "Preserve source-code evidence when it is present, and do "
                    "not invent repository or source-code details."
                ),
            ),
            (
                "user",
                f"Log data:\n{logs}",
            ),
        ]
    )

    return result

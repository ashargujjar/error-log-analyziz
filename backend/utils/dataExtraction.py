import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek

from schema.schema import errorStructureData


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


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


def extractErrorData(logs: str) -> errorStructureData:
    result = _get_structured_llm().invoke(
        [
            (
                "system",
                "Analyze the provided error log and return the required structured data.",
            ),
            (
                "user",
                f"Log data:\n{logs}",
            ),
        ]
    )

    return result

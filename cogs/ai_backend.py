import os
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langchain_tavily._utilities import TavilySearchAPIWrapper

load_dotenv()

openrouter_api_key = os.environ.get("openrouter_api_key")
tavily_api_key = os.environ.get("tavily_api_key")

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

CHAT_MODEL = "z-ai/glm-5-turbo"

_search = None


def _get_search() -> TavilySearch:
    global _search
    if _search is None:
        _search = TavilySearch(
            max_results=3,
            topic="general",
            include_answer="advanced",
            api_wrapper=TavilySearchAPIWrapper(tavily_api_key=tavily_api_key),
        )
    return _search


@tool
async def web_search(query: str) -> str:

    try:
        result = await _get_search().ainvoke({"query": query})
    except Exception:
        return "No results found."

    if isinstance(result, str):
        import json
        try:
            result = json.loads(result)
        except (ValueError, TypeError):
            return "No results found."
    if not isinstance(result, dict):
        return "No results found."

    parts = []
    answer = (result.get("answer") or "").strip()
    if answer:
        parts.append(f"Summary: {answer}")
    for hit in result.get("results", []):
        title = (hit.get("title") or "").strip()
        content = (hit.get("content") or "").strip()
        if not content:
            continue
        parts.append(f"- {title}: {content}" if title else f"- {content}")

    block = "\n".join(parts).strip()
    return block[:2000] if block else "No results found."


def make_chat(model: str = CHAT_MODEL, **kwargs) -> ChatOpenAI:

    return ChatOpenAI(
        model=model,
        base_url=OPENROUTER_BASE_URL,
        api_key=openrouter_api_key,
        **kwargs,
    )


def build_agent(system_prompt: str, model: str = CHAT_MODEL, **chat_kwargs):

    return create_agent(
        make_chat(model, **chat_kwargs),
        tools=[web_search],
        system_prompt=system_prompt,
    )


async def setup(bot):
    pass

import os
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openrouter import ChatOpenRouter
from langchain_tavily import TavilySearch

load_dotenv()

openrouter_api_key = os.environ["openrouter_api_key"]
tavily_api_key = os.environ["tavily_api_key"]

CHAT_MODEL = "openai/gpt-5.6-sol"

web_search = TavilySearch(
    name="web_search",
    max_results=10,
    include_answer="advanced",
    tavily_api_key=tavily_api_key,
)


def make_chat(model: str = CHAT_MODEL, **kwargs) -> ChatOpenRouter:

    return ChatOpenRouter(
        model=model,
        api_key=openrouter_api_key, 
        openrouter_provider=
        {"order" : ["azure"],
         "allow_fallbacks" : True},
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

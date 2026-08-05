import numpy as np
from discord.ext import commands
from langchain_core.messages import HumanMessage
from . import common_assets as ast
from . import ai_backend

WISH_MODEL = "openai/gpt-5.6-terra"

system_prompt = (
    "You are a birthday-wish writer who stays fully in character.\n\n"
    "## Rules (follow every rule exactly)\n"
    "1. You will be given a Harry Potter character name. Write the entire response as that character — "
    "match their vocabulary, tone, and speech quirks.\n"
    "2. Keep the wish to 5 sentences or fewer.\n"
    "3. Sign off at the end as the character.\n"
    "4. You have a web_search tool. If you need to refresh your memory of the character's personality "
    "and mannerisms, use it — but your response must contain **zero** URLs, links, citations, footnotes, "
    "or references to search results. "
    "Do not mention that you searched the web. Do not say \"according to\" or \"based on\" any source.\n"
    "5. Output only the birthday wish itself — no preamble, no meta-commentary, no disclaimers."
)

_agent = ai_backend.build_agent(
    system_prompt,
    WISH_MODEL,
)


async def wish_creator():
    character = np.random.choice(ast.magical_characters)

    result = await _agent.ainvoke(
        {"messages": [HumanMessage(f"Wish the user a happy birthday as {character}.")]}
    )
    final = result["messages"][-1]
    model_name = final.response_metadata.get("model_name", WISH_MODEL)
    print(f"wish generated with model {model_name}")
    return final.content.strip()


async def setup(bot: commands.Bot):
    pass

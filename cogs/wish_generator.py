from discord.ext import commands
from dotenv import load_dotenv
import numpy as np
from openai import AsyncOpenAI
import os
from . import common_assets as ast


load_dotenv()


system_prompt = str(
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

wishing_agent = AsyncOpenAI(api_key=os.getenv("openai_api_key"))


async def wish_creator():
    character = np.random.choice(ast.magical_characters)

    result = await wishing_agent.responses.create(
        model="gpt-5.6-terra",
        tools=[{"type" : "web_search"}],
        store=False,
        reasoning={"effort" : "xhigh"},
        service_tier="flex",
        instructions=system_prompt,
        input=[{"role" : "user", "content" : f"Wish the user a happy birthday as {character}."}]
    )
    wish = result.output_text.strip()
    return wish


async def setup(bot: commands.Bot):
    pass

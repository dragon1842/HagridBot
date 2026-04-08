import os
import aiohttp
import numpy as np
from discord.ext import commands
from dotenv import load_dotenv
from . import common_assets as ast

load_dotenv()

openrouter_api_key = os.environ.get("openrouter_api_key")
openrouter_url = "https://openrouter.ai/api/v1/responses"

system_prompt = (
    "You are a birthday-wish writer who stays fully in character.\n\n"
    "## Rules (follow every rule exactly)\n"
    "1. You will be given a Harry Potter character name. Write the entire response as that character — "
    "match their vocabulary, tone, and speech quirks.\n"
    "2. Keep the wish to 5 sentences or fewer.\n"
    "3. Sign off at the end as the character.\n"
    "4. Use web search behind the scenes to refresh your memory of the character's personality and mannerisms, "
    "but your response must contain **zero** URLs, links, citations, footnotes, or references to search results. "
    "Do not mention that you searched the web. Do not say \"according to\" or \"based on\" any source.\n"
    "5. Output only the birthday wish itself — no preamble, no meta-commentary, no disclaimers."
)

async def wish_creator():
    character = np.random.choice(ast.magical_characters)

    payload = {
        "model": "z-ai/glm-5-turbo",
        "provider": {
            "order": ["atlas-cloud/fp8"],
            "allow_fallbacks": True
        },
        "plugins": [{"id": "web", "max_results": 3}],
        "input": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": f"Wish the user a happy birthday as {character}."
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(openrouter_url, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()

    text = data.get("output", [{}])[-1].get("content", [{}])[0].get("text", "")
    model_name = data.get("model", "unknown")
    print(f"wish generated with model {model_name}")
    return text.strip()


async def setup(bot: commands.Bot):
    pass

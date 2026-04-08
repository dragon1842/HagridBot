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
    "You will be assigned a character from the fictional series \"Harry Potter\". "
    "You will impersonate the character, and respond to the given prompt as the character would. "
    "Your response should not be verbose. It should be no longer than 5 sentences. "
    "End the response by signing off as the character. "
    "Use web search to find snippets about the character's personality and speech patterns but do not include links or comments regarding the search results in your response."
    "to improve the authenticity of the wish."
)

async def wish_creator():
    character = np.random.choice(ast.magical_characters)

    payload = {
        "model": "deepseek/deepseek-v3.2",
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

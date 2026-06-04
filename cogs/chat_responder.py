import os
import asyncio
import aiohttp
from collections import defaultdict, deque
import discord
from discord.ext import commands
from dotenv import load_dotenv
from . import common_assets as ast

load_dotenv()

openrouter_api_key = os.environ.get("openrouter_api_key")
openrouter_url = "https://openrouter.ai/api/v1/responses"

ALLOWED_CHANNELS = {ast.bot_testing, ast.great_hall}
HISTORY_MAX = 100

system_prompt = (
    "You are responding to messages on Discord. Respond conversationally with a touch of snark, "
    "but stay appropriate. Do not ask follow-up questions or seek clarification — answer based on "
    "what was said. Do not introduce yourself, claim a persona, or identify yourself in any way. "
    "Keep replies concise."
)


async def chat_completion(history: list[dict], user_message: str) -> str:
    payload = {
        "model": "openrouter/auto",
        "plugins": [{"id": "web", "max_results": 3}],
        "input": [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": user_message},
        ],
    }
    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(openrouter_url, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()

    text = data.get("output", [{}])[-1].get("content", [{}])[0].get("text", "")
    return text.strip()


class ChatResponder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.histories: dict[int, deque] = defaultdict(lambda: deque(maxlen=HISTORY_MAX))
        self.locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.author.id != ast.dragon:
            return
        if message.channel.id not in ALLOWED_CHANNELS:
            return
        if self.bot.user not in message.mentions:
            return

        async with self.locks[message.channel.id]:
            history = self.histories[message.channel.id]
            user_content = message.content
            reply_text = await chat_completion(list(history), user_content)
            history.append({"role": "user", "content": user_content})
            history.append({"role": "assistant", "content": reply_text})

        await message.reply(reply_text)


async def setup(bot: commands.Bot):
    await bot.add_cog(ChatResponder(bot))

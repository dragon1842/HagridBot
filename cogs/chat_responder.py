import os
import re
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
    "Keep replies concise — 1 to 2 sentences at most. Respond only in plain text with casual "
    "punctuation — no markdown formatting and no links."
)

_CODE_BLOCK = re.compile(r"```[^\n]*\n?(.*?)```", re.DOTALL)
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_BARE_URL = re.compile(r"https?://\S+")
_INLINE_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*|__([^_]+)__")
_ITALIC = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)|(?<!_)_([^_\n]+)_(?!_)")
_STRIKE = re.compile(r"~~([^~]+)~~")
_HEADER = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_BLOCKQUOTE = re.compile(r"^>\s?", re.MULTILINE)
_LIST_ITEM = re.compile(r"^[ \t]*(?:[-*+]\s+|\d+\.\s+)", re.MULTILINE)
_HR = re.compile(r"^(?:-{3,}|\*{3,}|_{3,})\s*$", re.MULTILINE)
_EXTRA_NEWLINES = re.compile(r"\n{3,}")


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

    text = ""
    for item in reversed(data.get("output", [])):
        for part in item.get("content", []):
            if part.get("type") == "output_text" and part.get("text"):
                text = part["text"]
                break
        if text:
            break

    text = _CODE_BLOCK.sub(r"\1", text)
    text = _IMAGE.sub("", text)
    text = _LINK.sub("", text)
    text = _BARE_URL.sub("", text)
    text = _INLINE_CODE.sub(r"\1", text)
    text = _BOLD.sub(lambda m: m.group(1) or m.group(2), text)
    text = _ITALIC.sub(lambda m: m.group(1) or m.group(2), text)
    text = _STRIKE.sub(r"\1", text)
    text = _HEADER.sub("", text)
    text = _BLOCKQUOTE.sub("", text)
    text = _LIST_ITEM.sub("", text)
    text = _HR.sub("", text)
    text = _EXTRA_NEWLINES.sub("\n\n", text)
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
            if not reply_text:
                return
            history.append({"role": "user", "content": user_content})
            history.append({"role": "assistant", "content": reply_text})

        await message.reply(reply_text)


async def setup(bot: commands.Bot):
    await bot.add_cog(ChatResponder(bot))

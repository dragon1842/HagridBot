import asyncio
from collections import defaultdict, deque
import discord
from discord.ext import commands
from langchain_core.messages import HumanMessage, AIMessage
from . import common_assets as ast
from . import ai_backend

ALLOWED_CHANNELS = {ast.bot_testing, ast.great_hall}
HISTORY_MAX = 100

system_prompt = (
    "You are responding to messages on Discord. Respond conversationally but with a snarky tone," 
    "make use of memes and pop culture references when appropriate,"
    "with the goal of giving your responses a humorous and snarky edge. aim for a teasing tone"
    "but stay appropriate. Do not ask follow-up questions or seek clarification — answer based on "
    "what was said. Do not introduce yourself, claim a persona, or identify yourself in any way. "
    "Keep replies concise — 1 to 2 sentences at most. Respond only in plain text with casual "
    "punctuation — no markdown formatting and no links. You have a web_search tool; use it only "
    "when a message actually needs facts, and never quote, cite, or mention that you searched."
)


class ChatResponder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.histories: dict[int, deque] = defaultdict(lambda: deque(maxlen=HISTORY_MAX))
        self.locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.agent = ai_backend.build_agent(
            system_prompt = system_prompt, 
            model = "deepseek/deepseek-v4-pro"
        )

    async def chat_completion(self, history: list, user_message: str) -> str:
        result = await self.agent.ainvoke(
            {"messages": [*history, HumanMessage(user_message)]}
        )
        return result["messages"][-1].content.strip()

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
            reply_text = await self.chat_completion(list(history), user_content)
            if not reply_text:
                return
            history.append(HumanMessage(user_content))
            history.append(AIMessage(reply_text))

        await message.reply(reply_text)


async def setup(bot: commands.Bot):
    await bot.add_cog(ChatResponder(bot))

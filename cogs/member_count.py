import asyncio
import discord
from discord.ext import commands
from .variables import *

class MemberCount(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild = guild_id
        self.staff_channel = 825822128771301426
    
    async def fetch_and_update_count(self, bot: commands.Bot):
        while True:
            guild_object = await bot.fetch_guild(self.guild)
            member_count = guild_object.member_count
            channel = guild_object.get_channel(self.staff_channel) or await guild_object.fetch_channel(self.staff_channel)
            count_embed  = discord.Embed(title="Current Member Count", 
                                         description=f"The current member count is: **{member_count}**", color=discord.Color.blue())
            await channel.send(embed=count_embed)
            await asyncio.sleep(900)

async def setup(bot: commands.Bot):
    cog = MemberCount(bot)
    await bot.add_cog(cog)

    async def _start_loop():
        await bot.wait_until_ready()
        await cog.fetch_and_update_count(bot)
    bot.loop.create_task(_start_loop())
import discord
from discord.ext import commands, tasks
from . import common_assets as ast


class introduction_message(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.guild = None
        self.channel = None
        self.error_channel = None
        self.previous_message_id = None
        self.repetitive_intro_message.start()


    async def cog_load(self):
        self.guild = await self.bot.fetch_guild(ast.guild_id)
        self.channel = await self.guild.fetch_channel(ast.introductions)
        self.error_channel = await self.guild.fetch_channel(ast.bot_testing)


    async def cog_unload(self):
        self.repetitive_intro_message.cancel()


    @tasks.loop(hours=12)
    async def repetitive_intro_message(self):
        if self.previous_message_id is not None:
            try:
                old_message = self.channel.fetch_message(self.previous_message_id)
                await old_message.delete()
            except Exception as e:
                self.error_channel.send(f"Unable to delete old introduction reminder for reason: {e}")
                return

        intro_embed = discord.Embed(
            title="Welcome, firs' years!",
            description=f"Welcome to ther server, feel free to have a look around."
                f"You may introduce yerselves in this channel, usin' either the template in the pinned messages or one of yer own!"
                f"If you fancy a chat, check out your common rooms, or the <#{ast.great_hall}>!",
            colour=discord.colour.parse_hex_number("#ff4a70")
        )
        intro_embed.set_footer("No ditherin' here please, move along!")

        try:
            previous_message = await self.channel.send(intro_embed)
            self.previous_message_id = previous_message.id
        except Exception as e:
            self.error_channel.send(f"Unable to send introduction reminder for reason: {e}")


    @repetitive_intro_message.before_loop
    async def wait_before_intro(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    cog = (introduction_message(bot))
    await bot.add_cog(cog)
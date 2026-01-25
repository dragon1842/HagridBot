import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os
from .variables import *


load_dotenv()
class translation_commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.gcp_api = os.getenv("gcp_translate_api_key")

    async def translate_message (self, message:str):
        url = "https://translation.googleapis.com/language/translate/v2"
        params = {"q": message,
                "target": "en"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, params={"key":self.gcp_api}, data=params) as response:
                if response.status != 200:
                    error_message  =  await response.text()
                    bot_guild = self.bot.get_guild(guild_id) or await self.bot.fetch_guild(guild_id)
                    error_channel = bot_guild.get_channel(bot_testing) or await bot_guild.fetch_channel(bot_testing)
                    error_channel.send(content=f"Google Cloud Platform has raised an exception: {response.status}\t{error_message}")
                translation_result = await response.json()
                translation_data = translation_result.get("data").get("translations")[0]
                return(translation_data.get("translatedText"), translation_data.get("detectedSourceLanguage"))
    
    @app_commands.command(name="translate", description="For the linguistically-challenged...")
    @app_commands.checks.cooldown(rate=1, per=15, key = lambda i: i.user.id)
    @app_commands.describe(text="What you want translated to English")
    async def translate(self, interaction:discord.Interaction, text:str):
        await interaction.response.defer(ephemeral=True)
        translated_result, initial_language = await self.translate_message(text)
        translate_embed = discord.Embed(colour=interaction.user.colour)
        translate_embed.add_field(name="Initial message:", value=text, inline=False)
        translate_embed.add_field(name="Translated message:", value=translated_result, inline=False)
        translate_embed.set_footer(text=f"Translated from {initial_language}")
        await interaction.followup.send(embed=translate_embed)
        return

async def setup(bot: commands.Bot):
    cog = translation_commands(bot)
    await bot.add_cog(cog)
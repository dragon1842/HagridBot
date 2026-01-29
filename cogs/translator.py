import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os
from textwrap import shorten
from .variables import *


load_dotenv()
class translation_commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.gcp_api_key = os.getenv("gcp_translate_api_key")

    async def translate_message (self, message:str):
        async with aiohttp.ClientSession() as session:
            async with session.post(url=r"https://translation.googleapis.com/language/translate/v2",
                                    params={"q":message,
                                            "target":"en",
                                            "key":self.gcp_api_key,
                                            "format":"text"}) as response:
                if response.status == 200:
                    trnslt_result = await response.json()
                    trnslt_data = trnslt_result.get("data").get("translations")[0]
                    trnslted_string = trnslt_data.get("translatedText")
                    trnslted_code = trnslt_data.get("detectedSourceLanguage")
                else:
                    error_message  =  await response.text()
                    bot_guild = self.bot.get_guild(guild_id) or await self.bot.fetch_guild(guild_id)
                    error_channel = bot_guild.get_channel(bot_testing) or await bot_guild.fetch_channel(bot_testing)
                    await error_channel.send(content=f"Google Cloud Platform has raised an exception: {response.status}\t{error_message}")
                    return
            
            async with session.post(url=r"https://translation.googleapis.com/language/translate/v2/languages",
                                    params={"target":"en",
                                            "key":self.gcp_api_key}) as response:
                if response.status == 200:
                    lngs_result = await response.json()
                    lngs_list = lngs_result.get("data").get("languages")
                    for i in lngs_list:
                        if trnslted_code in i.get("language"):
                            trnslted_lng = i.get("name")
                            break
                    else:
                        trnslted_lng = None
                else:
                    error_message  =  await response.text()
                    bot_guild = self.bot.get_guild(guild_id) or await self.bot.fetch_guild(guild_id)
                    error_channel = bot_guild.get_channel(bot_testing) or await bot_guild.fetch_channel(bot_testing)
                    await error_channel.send(content=f"Google Cloud Platform has raised an exception: {response.status}\t{error_message}")
                    return
                
            return (trnslted_string, trnslted_lng)
    
    @app_commands.command(name="translate", description="For the linguistically-challenged...")
    @app_commands.checks.cooldown(rate=1, per=15, key = lambda i: i.user.id)
    @app_commands.describe(text="What you want translated to English")
    async def translate(self, interaction:discord.Interaction, text:str):
        await interaction.response.defer(ephemeral=True)
        translated_result, initial_language = await self.translate_message(shorten(text=text, width=1024))
        translate_embed = discord.Embed(colour=interaction.user.colour)
        translate_embed.add_field(name="Initial message:", value=text, inline=False)
        translate_embed.add_field(name="Translated message:", value=translated_result, inline=False)
        if initial_language is None:
            translate_embed.set_footer(text="Source language could not be identified")
        else:
            translate_embed.set_footer(text=f"Translated from {initial_language}")
        await interaction.followup.send(embed=translate_embed)
        return

async def setup(bot: commands.Bot):
    cog = translation_commands(bot)
    await bot.add_cog(cog)
import asyncio
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os
from textwrap import shorten
import google.auth
import google.auth.transport.requests
from .variables import *


load_dotenv()

class translation_commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild = None
        self.error_channel = None
        self._credentials = None
        self._project_id = None

    async def cog_load(self):
        self.guild = await self.bot.fetch_guild(guild_id)
        self.error_channel = await self.guild.fetch_channel(bot_testing)
        self._credentials, self._project_id = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )

    async def _get_access_token(self) -> str:
        if not self._credentials.valid:
            await asyncio.get_event_loop().run_in_executor(
                None, self._credentials.refresh, google.auth.transport.requests.Request()
            )
        return self._credentials.token

    async def translate_message(self, message: str):
        token = await self._get_access_token()
        auth_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=f"https://translation.googleapis.com/v3/projects/{self._project_id}:translateText",
                headers=auth_headers,
                json={
                    "contents": [message],
                    "targetLanguageCode": "en",
                    "mimeType": "text/plain",
                    "transliterationConfig": {"enableTransliteration": True}
                }
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    translation = result["translations"][0]
                    trnslted_string = translation["translatedText"]
                    detected_code = translation.get("detectedLanguageCode")
                    trnslted_romanization = translation.get("transliteratedText")
                else:
                    error_message = await response.text()
                    await self.error_channel.send(content=f"Google Cloud Platform has raised an exception: {response.status}\t{error_message}")
                    return

            async with session.get(
                url=f"https://translation.googleapis.com/v3/projects/{self._project_id}/supportedLanguages",
                headers=auth_headers,
                params={"displayLanguageCode": "en"}
            ) as response:
                if response.status == 200:
                    lngs_result = await response.json()
                    lngs_list = lngs_result.get("languages", [])
                    for i in lngs_list:
                        if i.get("languageCode") == detected_code:
                            trnslted_lng = i.get("displayName")
                            break
                    else:
                        trnslted_lng = None
                else:
                    error_message = await response.text()
                    await self.error_channel.send(content=f"Google Cloud Platform has raised an exception: {response.status}\t{error_message}")
                    return

        return (trnslted_string, trnslted_lng, trnslted_romanization)

    @app_commands.command(name="translate", description="For the linguistically-challenged...")
    @app_commands.checks.cooldown(rate=1, per=15, key = lambda i: i.user.id)
    @app_commands.describe(text="What you want translated to English")
    async def translate(self, interaction: discord.Interaction, text: str):
        await interaction.response.defer(ephemeral=True)
        translated_result, initial_language, romanization = await self.translate_message(shorten(text=text, width=512, placeholder="..."))
        translate_embed = discord.Embed(colour=interaction.user.colour)
        translate_embed.add_field(name="Initial message:", value=text, inline=False)
        translate_embed.add_field(name="Translated message:", value=translated_result, inline=False)
        if romanization:
            translate_embed.add_field(name="Romanization:", value=romanization, inline=False)
        if initial_language is None:
            translate_embed.set_footer(text="Source language could not be identified")
        else:
            translate_embed.set_footer(text=f"Translated from {initial_language}")
        await interaction.followup.send(embed=translate_embed)
        return

    @app_commands.command(name="twanswate", description="Twanswate your messages uwu~")
    @app_commands.checks.cooldown(rate=1, per=15, key=lambda i:i.user.id)
    @app_commands.describe(text="Entew what you want twanswated~")
    async def twanswate(self, interaction:discord.Interaction, text:str):
        await interaction.response.defer(ephemeral=True)
        twanswate_embed = discord.Embed(title="Baka", description="lol did you really think that was going to work?", colour=interaction.user.colour)
        twanswate_embed.set_footer(text="use the correct command idiot")
        await interaction.followup.send(embed=twanswate_embed)
        return


async def setup(bot: commands.Bot):
    cog = translation_commands(bot)
    await bot.add_cog(cog)

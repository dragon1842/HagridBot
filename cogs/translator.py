import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os
from textwrap import shorten
import google.auth
from google.cloud import translate_v3 as translate
from google.api_core import exceptions as gcp_exceptions
from . import common_assets as ast


load_dotenv()

class translation_commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild = None
        self.error_channel = None
        self._client = None
        self._parent = None

    async def cog_load(self):
        self.guild = await self.bot.fetch_guild(ast.guild_id)
        self.error_channel = await self.guild.fetch_channel(ast.bot_testing)
        self._client = translate.TranslationServiceAsyncClient()
        _, project_id = google.auth.default()
        self._parent = f"projects/{project_id}/locations/global"

    async def cog_unload(self):
        await self._client.transport.close()

    async def translate_message(self, message: str):
        base = {
            "parent": self._parent,
            "contents": [message],
            "target_language_code": "en",
            "mime_type": "text/plain",
        }
        try:
            try:
                response = await self._client.translate_text(
                    request=translate.TranslateTextRequest(
                        **base,
                        transliteration_config=translate.TransliterationConfig(
                            enable_transliteration=True
                        ),
                    )
                )
            except gcp_exceptions.InvalidArgument:
                response = await self._client.translate_text(
                    request=translate.TranslateTextRequest(**base)
                )

            translation = response.translations[0]
            trnslted_string = translation.translated_text
            detected_code = translation.detected_language_code

            langs = await self._client.get_supported_languages(
                parent=self._parent, display_language_code="en"
            )
            trnslted_lng = None
            for lang in langs.languages:
                if lang.language_code == detected_code:
                    trnslted_lng = lang.display_name
                    break
        except gcp_exceptions.GoogleAPICallError as exc:
            await self.error_channel.send(
                content=f"Google Cloud Platform has raised an exception: {exc.code}\t{exc.message}"
            )
            return

        return (trnslted_string, trnslted_lng)

    @app_commands.command(name="translate", description="For the linguistically-challenged...")
    @ast.owner_bypass_cooldown(rate=1, per=15)
    @app_commands.describe(text="What you want translated to English")
    async def translate(self, interaction: discord.Interaction, text: str):
        await interaction.response.defer(ephemeral=True)
        result = await self.translate_message(shorten(text=text, width=512, placeholder="..."))
        if result is None:
            await interaction.followup.send(content="Something went wrong while translating. The professors have been notified.")
            return
        translated_result, initial_language = result
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

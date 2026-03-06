# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Bot

```bash
source venv/Scripts/activate   # Windows (Git Bash)
python main.py
```

Required `.env` keys:
- `hagridbot_token` — Discord bot token
- `OPENAI_API_KEY` — OpenRouter API key (used with deepseek-v3.2 via OpenRouter base URL)
- `TAVILY_API_KEY` — Tavily search API key (used by the wish generator agent)
- `gcp_translate_api_key` — Google Cloud Translation API key

There are no tests. Manual testing is done by running the bot and using Discord slash commands.

## Architecture

**`main.py`** — Entry point. Defines `BirthdayBot(commands.Bot)` with prefix `b!`. Auto-loads all `cogs/*.py` files (excluding `__init__.py`) via `setup_hook`. Syncs slash commands globally in `on_ready`. Global app command error handler sends unexpected errors to the `bot_testing` channel.

**`cogs/variables.py`** — Single source of truth for all hardcoded constants: Discord IDs (guild, channels, roles), custom emoji strings, the Harry Potter `magical_characters` numpy array, and the `images` array (filenames from `images/`). Imported with `from .variables import *` in every cog.

**`cogs/birthday_handling.py`** — Core birthday logic:
- `init_db()` — singleton aiosqlite connection to `bot.db` (WAL mode). Called by multiple cogs' `setup()`.
- `birthday_parser(bot)` — checks all distinct timezones in the DB, finds users whose birthday is today in their local timezone (handles Feb 29 → Mar 1 in non-leap years), verifies guild membership (deletes stale entries for departed members), returns list of `user_id`s to wish.
- `mark_sent(user_ids)` — updates `last_posted` to today's date (per user's timezone) to prevent duplicate wishes.
- `birthday_handling` cog — runs `wish_checker` loop every 600 seconds as a background task started in `setup()`.

**`cogs/wish_generator.py`** — LangChain agent (`create_agent`) using `ChatOpenAI` pointed at OpenRouter (`deepseek-v3.2`) with `TavilySearch`. Randomly picks a Harry Potter character from `magical_characters` and generates a birthday wish in that character's voice.

**`cogs/birthday_commands.py`** — `/birthday` slash command group (available to all members): `add`, `remove`, `show`, `show_nearest`, `on_date`. Uses a `confirmation_check` UI View (45s timeout) for destructive operations.

**`cogs/override_commands.py`** — `/override` slash command group (restricted to `dragon` user ID and `professors` role ID): admin versions of `add` and `remove` that target any member.

**`cogs/debug_commands.py`** — `/debug` slash command group (restricted to `dragon` user ID only): `force` (manually trigger wish cycle), `status` (DB info), `ping`. Also exposes `b!sync` prefix command to re-sync the slash command tree.

**`cogs/translator.py`** — `/translate` command using GCP Translation API v2 via `aiohttp`. Translates any text to English and reports the source language.

**`cogs/help_command.py`** — `/help` command with a paginated embed UI (4 pages).

## Database Schema

Single table in `bot.db`:
```sql
CREATE TABLE birthdays (
  user_id   INTEGER PRIMARY KEY,
  month     INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
  day       INTEGER NOT NULL CHECK (day BETWEEN 1 AND 31),
  timezone  TEXT NOT NULL,
  last_posted TEXT DEFAULT ''   -- ISO date string, prevents duplicate wishes
);
```

## Access Control

| Command group | Who can use |
|---|---|
| `/birthday`, `/help`, `/translate` | All guild members |
| `/override` | `dragon` user ID **or** `professors` role ID |
| `/debug`, `b!sync` | `dragon` user ID only |

`dragon` and `professors` are user/role IDs defined in `cogs/variables.py`.

## Key Patterns

- **Interaction flow**: Always `defer()` first, then use `followup.send()` / `edit_original_response()`. Check `interaction.response.is_done()` before choosing between `followup` and `response`.
- **Guild member lookup**: Always try cache first (`guild.get_member(id)`), then fall back to `await guild.fetch_member(id)`. On `discord.NotFound`, delete the stale DB entry.
- **Adding a new cog**: Create `cogs/your_cog.py` with an `async def setup(bot)` function. It will be auto-loaded — no registration needed in `main.py`.
- **Slash command groups**: Register via `bot.tree.add_command(cog.group)` in `setup()`, wrapped in `try/except app_commands.CommandAlreadyRegistered`.
- **Error reporting**: Unexpected errors are sent to the `bot_testing` channel (ID in `variables.py`).

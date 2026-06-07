# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## General

- Respect `.gitignore` — do not read, search, or reference any files excluded by `.gitignore`.

## Running the Bot

```bash
source venv/Scripts/activate   # Windows (Git Bash)
python main.py
```

Required `.env` keys:
- `hagridbot_token` — Discord bot token
- `openrouter_api_key` — OpenRouter API key (used via LangChain's `ChatOpenAI` pointed at the OpenRouter base URL; see `cogs/ai_backend.py`)
- `tavily_api_key` — Tavily API key for web search (`langchain-tavily`). Read at import time in `cogs/ai_backend.py` via `os.environ[...]`, so the bot fails fast at startup if it's missing.
- `GOOGLE_APPLICATION_CREDENTIALS` — path to a GCP service account JSON key file, used for Google Cloud Translation API v3 (ADC via `google.auth.default()`)

There are no tests. Manual testing is done by running the bot and using Discord slash commands.

## Architecture

**`main.py`** — Entry point. Defines `BirthdayBot(commands.Bot)` with prefix `b!`. Auto-loads all `cogs/*.py` files (excluding `__init__.py`) via `setup_hook`. Syncs slash commands globally in `on_ready`. Global app command error handler sends unexpected errors to the `bot_testing` channel.

**`cogs/common_assets.py`** — Single source of truth for all hardcoded constants: Discord IDs (guild, channels, roles), custom emoji strings, the Harry Potter `magical_characters` numpy array, and the `images` array (filenames from `images/`). Also defines the `owner_bypass_cooldown(rate, per)` decorator (skips cooldowns for the `dragon` user ID). Imported as `from . import common_assets as ast` in every cog. Has a no-op `setup()` so the auto-loader can import it as an extension.

**`cogs/birthday_handling.py`** — Core birthday logic:
- `init_db()` — singleton aiosqlite connection to `bot.db` (WAL mode). Called by multiple cogs' `setup()`.
- `birthday_parser(bot)` — checks all distinct timezones in the DB, finds users whose birthday is today in their local timezone (handles Feb 29 → Mar 1 in non-leap years), verifies guild membership (deletes stale entries for departed members), returns list of `user_id`s to wish.
- `mark_sent(user_ids)` — updates `last_posted` to today's date (per user's timezone) to prevent duplicate wishes.
- `birthday_handling` cog — runs `wish_checker` loop every 600 seconds as a background task started in `setup()`.

**`cogs/ai_backend.py`** — Shared LangChain backend for the AI cogs (not a cog itself; has a no-op `setup()`). `make_chat()` builds a `ChatOpenAI` bound to OpenRouter (model pinned to `z-ai/glm-5-turbo`; extra kwargs like `extra_body` pass through for OpenRouter provider routing). `web_search` is a module-level `TavilySearch` instance (`langchain-tavily`, constructed with `tavily_api_key=` directly — no separate API-wrapper object, and `name="web_search"` so it matches the cogs' system-prompt references) passed straight to the agent as a tool; the model receives Tavily's raw results (which include source URLs) and decides how to use them. **There is no longer a wrapper stripping URLs** — keeping the final reply link-free now relies solely on the system prompts forbidding markdown/links. `build_agent(system_prompt, model, **chat_kwargs)` wraps a chat model + `web_search` into a `langchain.agents.create_agent` tool-calling agent (a `CompiledStateGraph`): the model decides per-turn whether to search and authors the final reply itself. Invoke with `{"messages": [...]}`; the reply is the last message's `.content`. Invoke with `{"messages": [...]}`; the reply is the last message's `.content`.

**`cogs/wish_generator.py`** — `wish_creator()` async function. Randomly picks a Harry Potter character from `magical_characters` and invokes an `ai_backend.build_agent` agent (using `WISH_MODEL` + the original OpenRouter fp8 provider routing via `extra_body`) to write a birthday wish in that character's voice. The agent may call `web_search` to refresh the character's mannerisms if it judges it necessary. The wish's system prompt forbids markdown/links, which is what keeps the output link/citation-free (the model now sees source URLs in the raw Tavily results, so this is a prompt-level guarantee).

**`cogs/chat_responder.py`** — `ChatResponder` cog. Listens for messages from the `dragon` user ID that @-mention the bot in allowed channels (`bot_testing`, `great_hall`), keeps per-channel conversation history (a `deque` of LangChain `HumanMessage`/`AIMessage`, max 100), serialised by a per-channel `asyncio.Lock`. Each turn invokes an `ai_backend.build_agent` agent with the history; the agent calls `web_search` only when the message needs facts, then replies in plain text (system prompt forbids markdown/links). Only the user turn and the final reply are stored back into history (not intermediate tool calls). No post-hoc regex stripping and no URL stripping on the tool output — the system prompt forbidding links is the sole thing keeping replies link-free.

**`cogs/birthday_commands.py`** — `/birthday` slash command group (available to all members): `add`, `remove`, `show`, `show_nearest`, `on_date`. Uses a `confirmation_check` UI View (45s timeout) for destructive operations.

**`cogs/override_commands.py`** — `/override` slash command group (restricted to `dragon` user ID and `professors` role ID): admin versions of `add` and `remove` that target any member.

**`cogs/debug_commands.py`** — `/debug` slash command group (restricted to `dragon` user ID only): `force` (manually trigger wish cycle), `status` (DB info), `ping`. Also exposes `b!sync` prefix command to re-sync the slash command tree.

**`cogs/translator.py`** — `/translate` command using GCP Translation API v3 via the official async client (`google.cloud.translate_v3.TranslationServiceAsyncClient`), which manages the credential/token lifecycle internally (ADC; `google.auth.default()` is still used only to get the project ID for the `parent` resource path). Translates any text to English and reports the source language. The request enables `transliteration_config` so romanized input (e.g. "kaise ho" typed in Latin script) is interpreted and its language autodetected; on `InvalidArgument` it retries without transliteration. Returns only the original text, the translation, and the detected language (no romanization field).

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

`dragon` and `professors` are user/role IDs defined in `cogs/common_assets.py`.

## Key Patterns

- **Interaction flow**: Always `defer()` first, then use `followup.send()` / `edit_original_response()`. Check `interaction.response.is_done()` before choosing between `followup` and `response`.
- **Guild member lookup**: Always try cache first (`guild.get_member(id)`), then fall back to `await guild.fetch_member(id)`. On `discord.NotFound`, delete the stale DB entry.
- **Adding a new cog**: Create `cogs/your_cog.py` with an `async def setup(bot)` function. It will be auto-loaded — no registration needed in `main.py`.
- **Slash command groups**: Register via `bot.tree.add_command(cog.group)` in `setup()`, wrapped in `try/except app_commands.CommandAlreadyRegistered`.
- **Error reporting**: Unexpected errors are sent to the `bot_testing` channel (ID in `common_assets.py`).

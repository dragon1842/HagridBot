import aiosqlite, discord
from discord.ext import commands, tasks
from datetime import datetime, timezone
import numpy as np
from zoneinfo import ZoneInfo
from .wish_generator import wish_creator
from . import common_assets as ast


db_path = "bot.db"
db: aiosqlite.Connection | None = None

create_sql = """
CREATE TABLE IF NOT EXISTS birthdays (
  user_id INTEGER PRIMARY KEY,
  month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
  day   INTEGER NOT NULL CHECK (day BETWEEN 1 AND 31),
  timezone TEXT NOT NULL,
  last_posted TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_birthdays ON birthdays(timezone, month, day);
"""

async def init_db():
    global db
    if db is None:
        db = await aiosqlite.connect(db_path)
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        await db.executescript(create_sql)
        await db.commit()
    return db

def is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


async def birthday_parser(bot: discord.Client) -> list[int]:
    global db
    if db is None:
        db = await init_db()

    guild = bot.get_guild(ast.guild_id) or await bot.fetch_guild(ast.guild_id)
    utc_now = datetime.now(timezone.utc)

    tzs: list[str] = []
    async with db.execute("SELECT DISTINCT timezone FROM birthdays") as cur:
        async for (tz,) in cur:
            tzs.append(tz)

    if not tzs:
        return []

    to_wish_candidates: list[int] = []

    for tz in tzs:
        try:
            z = ZoneInfo(tz)
        except Exception:
            z = timezone.utc

        local_now = utc_now.astimezone(z)
        ly, lm, ld = local_now.year, local_now.month, local_now.day
        today_key = local_now.date().isoformat()
        q_month, q_day = (3, 1) if (lm == 3 and ld == 1 and not is_leap_year(ly)) else (lm, ld)

        async with db.execute(
            """
            SELECT user_id
            FROM birthdays
            WHERE timezone = ? AND month = ? AND day = ?
              AND (last_posted IS NULL OR last_posted = '' OR last_posted != ?)
            """,
            (tz, q_month, q_day, today_key),
        ) as cur:
            async for (user_id,) in cur:
                to_wish_candidates.append(user_id)

    if not to_wish_candidates:
        return []

    to_wish: list[int] = []
    to_delete: list[int] = []

    for uid in to_wish_candidates:
        member = guild.get_member(uid)
        if not member:
            try:
                member = await guild.fetch_member(uid)
            except discord.NotFound:
                member = None
            except (discord.Forbidden, discord.HTTPException):
                member = None

        if member:
            to_wish.append(uid)
        else:
            to_delete.append(uid)

    if to_delete:
        qmarks = ",".join("?" for _ in to_delete)
        await db.execute(f"DELETE FROM birthdays WHERE user_id IN ({qmarks})", to_delete)

    await db.commit()
    return to_wish

async def mark_sent(user_ids: list[int]) -> None:
    if not user_ids:
        return

    global db
    if db is None:
        db = await init_db()

    utc_now = datetime.now(timezone.utc)

    qmarks = ",".join("?" for _ in user_ids)
    async with db.execute(
        f"SELECT user_id, timezone FROM birthdays WHERE user_id IN ({qmarks})",
        user_ids,
    ) as cur:
        rows = await cur.fetchall()

    for uid, tz in rows:
        try:
            z = ZoneInfo(tz)
        except Exception:
            z = timezone.utc
        today_key = utc_now.astimezone(z).date().isoformat()
        await db.execute(
            "UPDATE birthdays SET last_posted = ? WHERE user_id = ?",
            (today_key, uid),
        )

    await db.commit()


async def checkpoint_wal():
    global db
    if db is None:
        db = await init_db()
    await db.execute("PRAGMA wal_checkpoint(FULL);")
    await db.commit()



class birthday_handling(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.guild = None
        self.channel = None
        self.error_channel = None
        self.wish_checker.start()

    async def cog_load(self):
        self.guild = await self.bot.fetch_guild(ast.guild_id)
        self.channel = await self.guild.fetch_channel(ast.clock_tower)
        self.error_channel = await self.guild.fetch_channel(ast.bot_testing)


    async def cog_unload(self):
        self.wish_checker.cancel()


    async def wish_sender(self, to_wish):
        try:

            for i in to_wish:
                birthday_member = self.guild.get_member(i) or await self.guild.fetch_member(i)
                avatar_url = birthday_member.avatar.url

                birthday_embed = discord.Embed(title=f"Happy Birthday {birthday_member.name}!",
                    description=await wish_creator(),
                    colour=birthday_member.colour)
                birthday_embed.set_thumbnail(url=avatar_url)
                birthday_image_selector = np.random.choice(ast.images)
                birthday_image_path = ast.images_dir / f"{birthday_image_selector}"
                birthday_image_file = discord.File(birthday_image_path, filename=birthday_image_path.name)
                birthday_embed.set_image(url=f"attachment://{birthday_image_file.filename}")
                await self.channel.send(
                    birthday_member.mention,
                    file=birthday_image_file,
                    embed=birthday_embed,
                    allowed_mentions=discord.AllowedMentions(users=True),
                )

            await mark_sent(to_wish)

        except Exception as e:
            await self.error_channel.send(f"{ast.alert_emoji} Wishing Error: \n{e}")


    @tasks.loop(minutes=10)
    async def wish_checker(self):
            await checkpoint_wal()
            try:
                to_wish = await birthday_parser(self.bot)
                if to_wish:
                    await self.wish_sender(to_wish)
            except Exception:
                pass
    

    @wish_checker.before_loop
    async def wait_before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await init_db()
    cog = (birthday_handling(bot))
    await bot.add_cog(cog)
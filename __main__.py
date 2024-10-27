from __future__ import annotations

import asyncio
import contextlib
import os
from pathlib import Path

import aiohttp
import asyncpg
import dotenv
import jishaku
from amari import AmariClient

from core.bot import Giftify
from core.db import db_init
from core.log_handler import LogHandler

try:
    import uvloop
except ImportError:  # Windows
    pass
else:
    uvloop.install()

dotenv.load_dotenv()

jishaku.Flags.HIDE = True
jishaku.Flags.RETAIN = True
jishaku.Flags.NO_UNDERSCORE = True
jishaku.Flags.NO_DM_TRACEBACK = True


EXTENSIONS: tuple[str, ...] = (
    "meta",
    "settings",
    "timers",
    "giveaways",
    "donations",
    "raffles",
    "logger",
    "webserver",
)

async def main() -> None:
    async with aiohttp.ClientSession() as session, asyncpg.create_pool(
        dsn=os.environ["POSTGRESQL_DSN"],
        command_timeout=300,
        min_size=1,
        max_size=20,
        init=db_init,
        statement_cache_size=0,
    ) as pool, LogHandler() as log_handler, AmariClient(os.environ["AMARI_TOKEN"]) as amari_client, Giftify(
        log_handler=log_handler, pool=pool, session=session, amari_client=amari_client
    ) as bot:
        await bot.load_extension("jishaku")
        await bot.load_extension("cogs.timer_manager")

        for extension in EXTENSIONS:
            await bot.load_extension(f"cogs.{extension}")
            bot.log_handler.log.info("Loaded %s", extension)

        await bot.start()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())

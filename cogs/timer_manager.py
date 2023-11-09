import asyncio
import datetime
import logging
from typing import Optional

import asyncpg
import discord
import sentry_sdk
from discord.ext import commands

from bot import Giftify
from models.timers import Timer

log = logging.getLogger("timers")


class TimerManager(commands.Cog):
    """A cog for starting and managing simple timers internally."""

    def __init__(self, bot: Giftify) -> None:
        self.bot = bot
        self._have_data = asyncio.Event()
        self._current_timer: Optional[Timer] = None
        self._task = bot.loop.create_task(self.dispatch_timers())

    def cog_unload(self) -> None:
        self._task.cancel()

    async def get_active_timer(self, *, days: int = 7) -> Optional[Timer]:
        query = """
                SELECT * FROM timers
                WHERE (expires AT TIME ZONE 'UTC') < (CURRENT_TIMESTAMP + $1::interval)
                ORDER BY expires
                LIMIT 1;
            """
        record = await self.bot.pool.fetchrow(query, datetime.timedelta(days=days))
        if record is not None:
            return Timer.from_record(record=record)

    async def wait_for_active_timers(self, *, days: int = 7) -> Timer:
        timer = await self.get_active_timer(days=days)
        if timer is not None:
            self._have_data.set()
            return timer

        self._have_data.clear()
        self._current_timer = None
        await self._have_data.wait()

        # At this point we always have data.
        return await self.get_active_timer(days=days)  # type: ignore

    async def call_timer(self, timer: Timer, *, manually: bool = False) -> None:
        await self.delete_timer(timer)

        event_name = f"{timer.event}_end"
        self.bot.dispatch(event_name, timer)

        if manually:
            if (
                self._current_timer
                and self._current_timer.message_id == timer.message_id
            ):
                self._task.cancel()
                self._task = self.bot.loop.create_task(self.dispatch_timers())

    async def create_timer(
        self,
        message_id: int,
        channel_id: int,
        guild_id: int,
        author_id: int,
        title: str,
        event: str,
        expires: datetime.datetime,
        pool: asyncpg.Pool,
    ) -> Timer:
        now = datetime.datetime.now(datetime.timezone.utc)
        delta = (expires - now).total_seconds()
        if delta <= 60:
            timer = Timer(
                message_id=message_id,
                channel_id=channel_id,
                guild_id=guild_id,
                author_id=author_id,
                event=event,
                title=title,
                expires=expires,
            )
            self.bot.loop.create_task(self.short_timer_optimisation(delta, timer))
            return timer

        timer = await Timer.create(
            message_id,
            channel_id,
            guild_id,
            author_id,
            event,
            title,
            expires,
            pool,
        )

        self._have_data.set()

        if self._current_timer and expires < self._current_timer.expires:
            # cancel the task and re-run it
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())

        return timer

    async def short_timer_optimisation(self, seconds: float, timer: Timer) -> None:
        await asyncio.sleep(seconds)
        event_name = f"{timer.event}_end"
        self.bot.dispatch(event_name, timer)

    async def get_timer(
        self, *, guild_id: int, channel_id: int, message_id: int
    ) -> Optional[Timer]:
        record = await self.bot.pool.fetchrow(
            "SELECT * FROM timers WHERE guild = $1 AND channel = $2 AND message = $3",
            guild_id,
            channel_id,
            message_id,
        )
        if record:
            return Timer.from_record(record=record)

    async def delete_timer(self, timer: Timer) -> None:
        await timer.end(self.bot.pool)

    async def cancel_timer(self, timer: Timer) -> None:
        await self.delete_timer(timer)

        if self._current_timer and self._current_timer.message_id == timer.message_id:
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())

    async def dispatch_timers(self) -> None:
        if not self.bot.is_ready():
            await self.bot.wait_until_ready()

        try:
            while not self.bot.is_closed():
                # can only asyncio.sleep for up to ~48 days reliably
                # so we're gonna cap it off at 40 days
                # see: http://bugs.python.org/issue20493
                timer = self._current_timer = await self.wait_for_active_timers(days=40)
                now = datetime.datetime.now(datetime.timezone.utc)

                if timer.expires >= now:
                    to_sleep = (timer.expires - now).total_seconds()
                    await asyncio.sleep(to_sleep)

                await self.call_timer(timer)

        except asyncio.CancelledError:
            raise
        except (OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError):
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())
        except Exception as error:
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())

            log.error("An error was raised while dispatching timers:", exc_info=error)
            sentry_sdk.capture_exception(error)


async def setup(bot: Giftify):
    await bot.add_cog(TimerManager(bot))

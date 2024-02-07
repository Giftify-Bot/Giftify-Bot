import logging
from typing import Tuple, Union

import asyncpg
import discord
import sentry_sdk
from discord import app_commands
from discord.ext import commands, tasks

from core.bot import Giftify
from core.tree import Interaction
from models.giveaways import Giveaway, GiveawayAction
from models.timers import Timer
from utils.constants import CROWN_EMOJI, GIFT_EMOJI, TIMER_EMOJI, TROPHY_EMOJI
from utils.view import GiveawayView

# Command imports
from .cancel import GiveawayCancel
from .end import GiveawayEnd
from .list import GiveawayList
from .reroll import GiveawayReroll
from .start import GiveawayStart
from .top import GiveawayTop

log = logging.getLogger("giveaways")


@app_commands.guild_only()
class GiveawayCog(
    GiveawayStart,
    GiveawayEnd,
    GiveawayReroll,
    GiveawayCancel,
    GiveawayTop,
    GiveawayList,
    name="giveaway",
):
    """Start and manage giveaways."""

    def __init__(self, bot: Giftify) -> None:
        self.bot = bot

        def key(bucket: Tuple[Union[discord.Member, discord.User], Giveaway]):
            return (bucket[0].id, bucket[1].message_id)

        self.messages_cooldown = commands.CooldownMapping.from_cooldown(1, 5, type=key)

        self.update_message_cache.add_exception_type(asyncpg.PostgresConnectionError)
        self.update_message_cache.start()

        super().__init__()

    async def cog_load(self):
        self.bot.cached_giveaways = [
            Giveaway(bot=self.bot, record=record)
            for record in await self.bot.pool.fetch(
                "SELECT * FROM giveaways WHERE messages_required > 0 AND ended = FALSE"
            )
        ]

        self.bot.add_view(GiveawayView())

    def cog_unload(self):
        self.update_message_cache.stop()

    async def interaction_check(self, interaction: Interaction) -> bool:
        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        if interaction.user.guild_permissions.manage_guild:
            return True

        config = await interaction.client.fetch_config(interaction.guild)
        for role in config.managers:
            if role in interaction.user.roles:
                return True
        else:
            await interaction.client.send(
                interaction,
                "You do not have permissions to use this command.",
                reason="error",
                ephemeral=True,
            )
            return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return

        relevant_giveaways = [
            giveaway
            for giveaway in self.bot.cached_giveaways
            if giveaway.messages_required
            and giveaway.messages_required > 0
            and giveaway.guild_id == message.guild.id
        ]

        for giveaway in relevant_giveaways:
            if (
                giveaway.allowed_message_channels
                and message.channel.id not in giveaway.allowed_message_channels
            ):
                continue
            retry_after = self.messages_cooldown.update_rate_limit(
                (message.author, giveaway)
            )
            if retry_after:
                continue

            if message.author.id in giveaway.messages:
                giveaway.messages[message.author.id] += 1
            else:
                giveaway.messages[message.author.id] = 1

    @commands.Cog.listener()
    async def on_giveaway_action(
        self,
        action: GiveawayAction,
        giveaway: Giveaway,
        action_author: Union[discord.Member, discord.User],
    ):
        guild = self.bot.get_guild(giveaway.guild_id)
        if not guild:
            return
        config = await self.bot.fetch_config(guild)
        if not config.logging:
            return

        embed = discord.Embed(title=f"Giveaway {action}", colour=config.color)
        host = await self.bot.get_or_fetch_user(giveaway.host_id)
        embed.add_field(
            name=f"{GIFT_EMOJI} Prize",
            value=giveaway.prize,
            inline=False,
        )
        embed.add_field(
            name=f"{TIMER_EMOJI} Ends At",
            value=discord.utils.format_dt(giveaway.ends, style="R"),
            inline=False,
        )
        if host:
            embed.add_field(
                name=f"{CROWN_EMOJI} Host", value=host.mention, inline=False
            )
        embed.add_field(
            name=f"{TROPHY_EMOJI} Winner Count",
            value=giveaway.winner_count,
            inline=False,
        )
        embed.set_author(
            name=f"Authored By {action_author.display_name} ({action_author.id})",
            icon_url=action_author.display_avatar,
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await self.bot.send_to_webhook(channel=config.logging, embed=embed)

    @tasks.loop(minutes=5)
    async def update_message_cache(self):
        giveaways = [
            (
                giveaway.messages,
                giveaway.guild_id,
                giveaway.channel_id,
                giveaway.message_id,
            )
            for giveaway in self.bot.cached_giveaways
            if giveaway.messages
        ]
        query = """UPDATE giveaways SET messages = $1
                   WHERE guild = $2 AND channel = $3 AND message = $4
                   """
        if giveaways:
            async with self.bot.pool.acquire(timeout=60) as conn:
                await conn.executemany(query, giveaways, timeout=60)

    @update_message_cache.before_loop
    async def before_update_message_cache(self):
        await self.bot.wait_until_ready()

    @update_message_cache.error
    async def on_update_message_cache_error(self, error: BaseException) -> None:
        log.exception("Error while updating message cache to database:", exc_info=error)
        sentry_sdk.capture_exception(error)

    @commands.Cog.listener()
    async def on_giveaway_end(self, timer: Timer):
        giveaway = await self.bot.fetch_giveaway(
            guild_id=timer.guild_id,
            channel_id=timer.channel_id,
            message_id=timer.message_id,
        )

        if giveaway is None:
            return

        if giveaway in self.bot.cached_giveaways:
            self.bot.cached_giveaways.remove(giveaway)

        self.bot.dispatch(
            "giveaway_action", GiveawayAction.END, giveaway, self.bot.user
        )

        await giveaway.end()


async def setup(bot: Giftify) -> None:
    await bot.add_cog(GiveawayCog(bot))

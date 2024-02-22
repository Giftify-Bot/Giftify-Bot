from __future__ import annotations

import datetime
import logging
import os
import sys
import traceback
from typing import TYPE_CHECKING, ClassVar, Optional

import aiohttp
import asyncpg
import discord
import sentry_sdk
from amari import AmariClient
from discord.ext import commands
from discord.utils import MISSING
from expiringdict import ExpiringDict
from sentry_sdk.integrations.logging import LoggingIntegration

from models.giveaway_settings import GuildConfig
from models.giveaways import Giveaway
from models.raffles import Raffle
from utils.constants import ERROR_EMOJI, SUCCESS_EMOJI, WARN_EMOJI
from utils.view import ConfirmationView

from .log_handler import LogHandler
from .tree import CommandTree

if TYPE_CHECKING:
    from cogs.timer_manager import TimerManager
    from models.donation_settings import GuildDonationConfig

OWNER_IDS = (747403406154399765,)


class GiftifyHelper:
    configs: ClassVar[list[GuildConfig]] = []
    donation_configs: ClassVar[list[GuildDonationConfig]] = []
    cached_giveaways: ClassVar[list[Giveaway]] = []
    webhook_cache: ClassVar[dict[discord.TextChannel, discord.Webhook]] = {}
    raffles_cache: ClassVar[dict[discord.Guild, list[Raffle]]] = ExpiringDict(max_len=100, max_age_seconds=300)

    pool: asyncpg.Pool
    user: discord.ClientUser
    amari_client: AmariClient

    """A helper class for Giftify's operations.

    This class provides methods to send interaction messages with embeds,
    fetch webhooks for a channel, and retrieve or fetch guild configuration.
    """

    async def send(
        self,
        interaction: discord.Interaction,
        message: str,
        reason: str = "success",
        ephemeral: bool = True,
        view: discord.ui.View = MISSING,
    ) -> None:
        """Sends an interaction message with embed.

        Parameters
        -----------
        interaction: discord.Interaction
            The interaction to respond to.
        message: str
            The response message to send.
        reason: str
            The reason to send the message, can be "warn", "error" or "success".
        ephemeral: bool
            If the response should be sent ephemerally.
        """
        emoji = WARN_EMOJI if reason == "warn" else ERROR_EMOJI if reason == "error" else SUCCESS_EMOJI
        colour = (
            discord.Colour.orange()
            if reason == "warn"
            else discord.Colour.red()
            if reason == "error"
            else discord.Colour.green()
        )
        embed = discord.Embed(description=f"> {emoji} {message}", colour=colour)

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, view=view, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)

    async def _get_webhook(self, channel: discord.TextChannel, force_create: bool = False) -> discord.Webhook:
        if not force_create and (webhook := self.webhook_cache.get(channel)):
            return webhook

        webhook_list = await channel.webhooks()
        if webhook_list:
            for hook in webhook_list:
                if hook.token and hook.user and hook.user.id == self.user.id:
                    self.webhook_cache[channel] = hook
                    return hook

        # If no suitable webhook is found, create a new one
        hook = await channel.create_webhook(name="Giftify Logging", avatar=await channel.guild.me.display_avatar.read())
        self.webhook_cache[channel] = hook
        return hook

    async def send_to_webhook(self, channel: discord.TextChannel, embed: discord.Embed) -> None:
        """Sends an embed to a webhook associated with the provided channel.

        Parameters
        -----------
        channel: discord.TextChannel
            The channel to send message to.

        """
        try:
            webhook = await self._get_webhook(channel)
            await webhook.send(
                embed=embed,
                username="Giftify Logging",
                avatar_url=self.user.display_avatar,
            )
        except discord.NotFound:
            webhook = await self._get_webhook(channel, force_create=True)
            await webhook.send(
                embed=embed,
                username="Giftify Logging",
                avatar_url=self.user.display_avatar,
            )

        except discord.HTTPException:
            return

    async def fetch_config(self, guild: discord.Guild) -> GuildConfig:
        """Looks up a guild config in cache or fetches if not found.

        Parameters
        -----------
        guild: discord.Guild
            The guild to look for.

        Returns
        ---------
        GuildConfig
            The retrieved guild config object.
        """
        config = discord.utils.get(self.configs, guild=guild)
        if not config:
            config = await GuildConfig.fetch(guild, self.pool)
            self.configs.append(config)

        return config

    def get_donation_config(self, guild: discord.Guild, category: str) -> Optional[GuildDonationConfig]:
        """Finds the donation config of a guild for some category.

        Parameters
        -----------
        guild: Guild
            The guild to which the category belongs.
        category: str
            The name of the category.

        Returns
        --------
        Optional[GuildDonationConfig]
            The fetched donation config.
        """
        for config in self.donation_configs:
            if config.guild == guild and config.category == category:
                return config

    def get_guild_donation_categories(self, guild: discord.Guild) -> list[str]:
        """Finds the donation categories of a guild.

        Parameters
        -----------
        guild: Guild
            The guild for which categories will be fetched.

        Returns
        --------
        list[str]
            The of names of donation categories.
        """
        return [config.category for config in self.donation_configs if config.guild == guild]

    async def fetch_raffle(self, guild: discord.Guild, name: str) -> Optional[Raffle]:
        """Finds a raffle in some guild.

        Parameters
        -----------
        guild: Guild
            The guild to which the raffle belongs.
        name: str
            The name of the raffle.

        Returns
        --------
        Optional[Raffle]
            The fetched raffle.
        """
        record = await self.pool.fetchrow("SELECT * FROM raffles WHERE guild = $1 AND name = $2", guild.id, name)
        if record is not None:
            return await Raffle.from_record(self, record=record)  # type: ignore

    async def fetch_raffles(self, guild: discord.Guild, use_cache: bool = True) -> list[Raffle]:
        """Fetch all the raffles in some guild

        Parameters
        -----------
        guild: Guild
            The guild for which raffles will be fetched.
        use_cache: bool
            Indicates wheter the bot should fetch the raffles from database or use internal cache.

        Returns
        --------
        list[Raffle]
            The of list of fetched raffles.
        """
        if guild in self.raffles_cache and use_cache:
            return self.raffles_cache[guild]

        records = await self.pool.fetch("SELECT * FROM raffles WHERE guild = $1", guild.id)
        raffles = [await Raffle.from_record(self, record=record) for record in records]  # type: ignore
        self.raffles_cache[guild] = raffles

        return raffles

    async def fetch_giveaway(self, *, guild_id: int, channel_id: int, message_id: int) -> Optional[Giveaway]:
        """Looks up a for a giveaway object in database.

        Parameters
        -----------
        message_id: int
            The ID of the giveaway message.

        Returns
        --------
        Optional[Giveaway]
            The retrieved giveaway object.
        """
        giveaway = discord.utils.get(
            self.cached_giveaways,
            guild_id=guild_id,
            channel_id=channel_id,
            message_id=message_id,
        )
        if giveaway is not None:
            return giveaway
        record = await self.pool.fetchrow(
            "SELECT * FROM giveaways WHERE guild = $1 AND channel = $2 AND message = $3",
            guild_id,
            channel_id,
            message_id,
        )
        if record is not None:
            giveaway = Giveaway(bot=self, record=record)  # type: ignore
            if giveaway.messages:
                self.cached_giveaways.append(giveaway)

            return giveaway

    async def running_giveaways(self, *, guild_id: Optional[int] = None, sort_by_ends: bool = True) -> list[Giveaway]:
        """Looks up a list of active giveaways in the database.

        Parameters
        -----------
        guild_id: Optional[int]
            The ID of the guild. If provided, fetches giveaways only for that guild.
        sort_by_ends: bool
            If True, the results will be sorted by the 'ends' column in ascending order.

        Returns
        --------
        list[Giveaway]
            The list of fetched active giveaways.
        """
        query = "SELECT * FROM giveaways WHERE ended = FALSE"
        if guild_id is not None:
            query += " AND guild = $1"
        if sort_by_ends:
            query += " ORDER BY ends ASC"

        if guild_id is not None:
            records = await self.pool.fetch(query, guild_id)
        else:
            records = await self.pool.fetch(query)

        return [Giveaway(bot=self, record=record) for record in records]  # type: ignore

    async def fetch_level(self, member: discord.Member, /) -> int:
        """Fetches user level from Amari Bot API.

        Parameters
        -----------
        member: discord.Member
            The member whose level is to be fetched.

        Returns
        ---------
        int
            The retrieved level.
        """
        try:
            user = await self.amari_client.fetch_user(member.guild.id, member.id)
        except Exception:
            return 0
        else:
            return user.level or 0

    async def fetch_weekly_experience(self, member: discord.Member, /) -> int:
        """Fetches user's weekly experience from Amari Bot API.

        Parameters
        -----------
        member: discord.Member
            The member whose weekly experience is to be fetched.

        Returns
        ---------
        int
            The retrieved weekly experience.
        """
        try:
            user = await self.amari_client.fetch_user(member.guild.id, member.id)
        except Exception:
            return 0
        else:
            return user.weeklyexp or 0

    async def prompt(
        self,
        message: str,
        *,
        interaction: discord.Interaction[Giftify],
        success_message: str,
        cancel_message: str,
        timeout: float = 60.0,
    ) -> Optional[bool]:
        """An interactive reaction confirmation dialog.

        Parameters
        -----------
        message: str
            The message to show along with the prompt.
        timeout: float
            How long to wait before returning.
        interaction: Interaction
            The interaction object to handle the confirmation dialog.
        success_message: str
            The message to show when the user clicks Confirm.
        cancel_message: str
            The message to show when the user clicks Cancel.

        Returns
        --------
        Optional[bool]
            ``True`` if explicit confirm,
            ``False`` if explicit deny,
            ``None`` if deny due to timeout
        """

        view = ConfirmationView(
            timeout=timeout,
            interaction=interaction,
            success_message=success_message,
            cancel_message=cancel_message,
        )
        view.message = await self.send(interaction, message, view=view, reason="warn")
        await view.wait()
        return view.value


class Giftify(GiftifyHelper, commands.AutoShardedBot):
    user: discord.ClientUser

    colour: int = 0xCB3045
    __version_info__ = "1.2.5"

    def __init__(
        self,
        *,
        log_handler: LogHandler,
        pool: asyncpg.Pool,
        session: aiohttp.ClientSession,
        amari_client: AmariClient,
    ) -> None:
        self._log_handler = log_handler
        self._pool = pool
        self._session = session
        self._amari_client = amari_client

        intents = discord.Intents(messages=True, emojis=True, guilds=True)
        allowed_mentions = discord.AllowedMentions(everyone=False, roles=False, users=True, replied_user=False)
        member_cache_flags = discord.MemberCacheFlags.from_intents(intents=intents)

        sentry_sdk.init(
            dsn=os.environ["SENTRY_DSN"],
            integrations=[
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR,
                )
            ],
            traces_sample_rate=1.0,
        )

        super().__init__(
            command_prefix=commands.when_mentioned,
            tree_cls=CommandTree,
            help_command=None,
            description="A giveaway bot for hosting giveaways.",
            intents=intents,
            allowed_mentions=allowed_mentions,
            chunk_guilds_at_startup=False,
            max_messages=None,
            activity=discord.CustomActivity(name="\N{LINK SYMBOL} https://giftifybot.vercel.app"),
            member_cache_flags=member_cache_flags,
            owner_ids=OWNER_IDS,
        )

    @property
    def log_handler(self) -> LogHandler:
        return self._log_handler

    @property
    def pool(self) -> asyncpg.Pool:
        return self._pool

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session

    @property
    def amari_client(self) -> AmariClient:
        return self._amari_client

    @property
    def timer_cog(self) -> TimerManager:
        return self.get_cog("TimerManager")  # type: ignore

    def run(self) -> None:
        msg = "Please use `.start()` instead."
        raise NotImplementedError(msg)

    async def on_ready(self) -> None:
        self.log_handler.log.info("%s got a ready event at %s", self.user.name, datetime.datetime.now())

    async def on_resume(self) -> None:
        self.log_handler.log.info("%s got a resume event at %s", self.user.name, datetime.datetime.now())

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandInvokeError):
            origin_ = error.original
            assert ctx.command is not None
            if not isinstance(origin_, discord.HTTPException):
                print(f"In {ctx.command.qualified_name}:", file=sys.stderr)
                traceback.print_tb(origin_.__traceback__)
                print(f"{origin_.__class__.__name__}: {origin_}", file=sys.stderr)
                sentry_sdk.capture_exception(error)

    async def start(self) -> None:
        await super().start(token=os.environ["TOKEN"], reconnect=True)

    async def setup_hook(self) -> None:
        self.start_time: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)

        self.bot_app_info = await self.application_info()
        self.owner_ids = OWNER_IDS

    async def get_or_fetch_user(self, user_id: int) -> Optional[discord.User]:
        """Looks up a user in cache or fetches if not found.

        Parameters
        -----------
        user_id: int
            The user ID to search for.

        Returns
        ---------
        Optional[User]
            The user or None if not found.
        """

        user = self.get_user(user_id)
        if user is not None:
            return user

        try:
            user = await self.fetch_user(user_id)
        except discord.HTTPException:
            return None
        else:
            return user

    async def get_or_fetch_member(self, guild: discord.Guild, member_id: int) -> Optional[discord.Member]:
        """Looks up a member in cache or fetches if not found.

        Parameters
        -----------
        guild: Guild
            The guild to look in.
        member_id: int
            The member ID to search for.

        Returns
        ---------
        Optional[Member]
            The member or None if not found.
        """

        member = guild.get_member(member_id)
        if member is not None:
            return member

        shard: discord.ShardInfo = self.get_shard(guild.shard_id)  # type: ignore  # will never be None
        if shard.is_ws_ratelimited():
            try:
                member = await guild.fetch_member(member_id)
            except discord.HTTPException:
                return None
            else:
                return member

        members = await guild.query_members(limit=1, user_ids=[member_id], cache=True)
        if not members:
            return None
        return members[0]

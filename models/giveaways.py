from __future__ import annotations

import contextlib
import datetime
import logging
import random
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional

import asyncpg
import discord

from core.tree import Interaction
from models.giveaway_settings import ChannelConfig, GuildConfig
from utils.constants import GIFT_EMOJI
from utils.exceptions import GiveawayError
from utils.functions import bold, filter_none, safe_format
from utils.view import BaseView, GiveawayView

if TYPE_CHECKING:
    from core.bot import Giftify

log = logging.getLogger(__name__)


class Giveaway:
    """
    Represents a giveaway object.

    Attributes
    ----------
    bot: Giftify
        The bot instance to handle the giveaway.
    guild_id: int
        The ID of the guild (server) where the giveaway is hosted.
    channel_id: int
        The ID of the channel where the giveaway is hosted.
    message_id: int
        The ID of the giveaway message.
    extra_message_id: int
        The ID of the extra message with giveaway.
    host_id: int
        The ID of the user hosting the giveaway.
    donor_id: int
        The ID of the user donating for the giveaway.
    prize: int
        The prize of the giveaway.
    winner_count: int
        The number of winners for the giveaway.
    winners: List[int]
        The winners of the giveaway.
    participants: List[int]
        The IDs participants for the giveaway.
    ended: bool
        Indicates whether the giveaway has ended.
    ends: datetime.datetime
        The timestamp when the giveaway will be ended.
    required_roles: List[int]
        The list of role IDs required to participate in the giveaway.
    blacklisted_roles: List[int]
        The list of role IDs excluded from participating in the giveaway.
    bypass_roles: List[int]
        The list of user IDs exempted from giveaway restrictions.
    multiplier_roles: Optional[dict]
        A dictionary containing multiplier_roles criteria for the giveaway.
    messages: Optional[dict]
        A dictionary containing message-based criteria for the giveaway.
    messages_required: Optional[int]
        The number of messages required to participate in the giveaway.
    allowed_message_channels: Optional[List[int]]
        The ID of the channels where the message count is tracked.
    amari: Optional[int]
        The required Amari XP to participate in the giveaway.
    weekly_amari: Optional[int]
        The required weekly Amari XP to participate in the giveaway.
    """

    __slots__ = (
        "bot",
        "guild_id",
        "channel_id",
        "message_id",
        "extra_message_id",
        "prize",
        "host_id",
        "donor_id",
        "winner_count",
        "winners",
        "participants",
        "ended",
        "ends",
        "required_roles",
        "blacklisted_roles",
        "bypass_roles",
        "multiplier_roles",
        "messages",
        "messages_required",
        "allowed_message_channels",
        "amari",
        "weekly_amari",
    )

    def __init__(self, *, bot: Giftify, record: asyncpg.Record) -> None:
        self.bot = bot
        self.guild_id: int = record["guild"]
        self.channel_id: int = record["channel"]
        self.message_id: int = record["message"]
        self.extra_message_id: int = record["extra_message"]
        self.prize: str = record["prize"]
        self.host_id: int = record["host"]
        self.donor_id: Optional[int] = record["donor"]
        self.winner_count: int = record["winner_count"]
        self.winners: List[int] = record["winners"]
        self.participants: List[int] = record["participants"]
        self.ended: bool = record["ended"]
        self.ends: datetime.datetime = record["ends"]
        self.required_roles: List[int] = record["required_roles"] or []
        self.blacklisted_roles: List[int] = record["blacklisted_roles"] or []
        self.bypass_roles: List[int] = record["bypass_roles"] or []
        self.multiplier_roles: Dict[int, int] = {
            int(role): entries for role, entries in record["multiplier_roles"].items() if entries > 1
        }
        self.messages: Dict[int, int] = {int(member): messages for member, messages in record["messages"].items()}
        self.messages_required: Optional[int] = record["messages_required"]
        self.allowed_message_channels: Optional[List[int]] = record["messages_channel"]
        self.amari: Optional[int] = record["amari"]
        self.weekly_amari: Optional[int] = record["weekly_amari"]

    def __eq__(self, other: Giveaway) -> bool:
        try:
            return (
                self.guild_id == other.guild_id
                and self.channel_id == other.channel_id
                and self.message_id == other.message_id
            )
        except AttributeError:
            return False

    def __hash__(self) -> int:
        return hash((self.guild_id, self.channel_id, self.message_id))

    def __repr__(self) -> str:
        return f"<Giveaway guild_id={self.guild_id} channel_id={self.channel_id} message_id={self.message_id}>"

    @property
    def jump_to_giveaway(self) -> discord.ui.View:
        url = f"https://discord.com/channels/{self.guild_id}/{self.channel_id}/{self.message_id}"
        view = BaseView(timeout=None)
        button = discord.ui.Button(label="Jump To Giveaway", url=url)
        view.add_item(button)
        return view

    @staticmethod
    def create_embed(  # noqa: C901
        interaction: Interaction,
        config: GuildConfig,
        duration: datetime.datetime,
        winners: int,
        prize: str,
        required_roles: List[discord.Role],
        blacklisted_roles: List[discord.Role],
        bypass_roles: List[discord.Role],
        multiplier_roles: Dict[discord.Role, int],
        messages_required: Optional[int] = None,
        allowed_message_channels: Optional[List[discord.TextChannel]] = None,
        amari: Optional[int] = None,
        weekly_amari: Optional[int] = None,
        donor: Optional[discord.Member] = None,
    ) -> discord.Embed:
        assert interaction.guild is not None

        description = f"Click the {config.reaction} button to join the giveaway!\nHosted By: {interaction.user.mention}\n"

        if donor:
            description += f"Donor: {donor.mention}\n"

        description += (
            f"Ends: {discord.utils.format_dt(duration, style='R')} ({discord.utils.format_dt(duration, style='f')})\n"
        )

        embed = discord.Embed(
            title=prize,
            description=description,
            colour=config.color,
            timestamp=duration,
        )
        embed.set_footer(
            text=f"{winners} winner(s) • Ends",
            icon_url=interaction.guild.icon or interaction.client.user.display_avatar,
        )
        requirements = ""
        if required_roles:
            requirements += f"Required Roles: {', '.join(role.mention for role in required_roles)}\n"
        if bypass_roles:
            requirements += f"Bypass Roles: {', '.join(role.mention for role in bypass_roles)}\n"

        if blacklisted_roles:
            requirements += f"Blacklisted Roles: {', '.join(role.mention for role in blacklisted_roles)}\n"
        if messages_required:
            requirements += f"Messages Required: **{messages_required}** message(s) (5s cooldown)\n"
            if allowed_message_channels:
                requirements += f"Allowed Channels: {', '.join(f'<#{c.id}>' for c in allowed_message_channels)}\n"

        if amari:
            requirements += f"Amari Level: {amari}\n"
        if weekly_amari:
            requirements += f"Weekly Amari: {weekly_amari} XP Points\n"

        if requirements:
            embed.add_field(name="Requirements", value=requirements, inline=False)

        if multiplier_roles:
            multiplier_roles_mention = "\n".join(
                [f"- {entry}x ・ {role.mention}" for role, entry in multiplier_roles.items()]
            )
            embed.add_field(name="Bonus Entries", value=multiplier_roles_mention, inline=False)

        return embed

    @classmethod
    async def start(
        cls,
        interaction: Interaction,
        duration: datetime.datetime,
        winners: int,
        prize: str,
        config: GuildConfig,
        channel_config: Optional[ChannelConfig],
        required_roles: Optional[List[discord.Role]] = None,
        blacklisted_roles: Optional[List[discord.Role]] = None,
        bypass_roles: Optional[List[discord.Role]] = None,
        multiplier_roles: Optional[Dict[discord.Role, int]] = None,
        messages_required: Optional[int] = None,
        allowed_message_channels: Optional[List[discord.TextChannel]] = None,
        amari: Optional[int] = None,
        weekly_amari: Optional[int] = None,
        image: Optional[discord.Attachment] = None,
        donor: Optional[discord.Member] = None,
        ping: bool = False,
        message: Optional[str] = None,
    ) -> Giveaway:
        assert isinstance(interaction.channel, discord.TextChannel)
        assert interaction.guild is not None

        required_roles = filter_none(required_roles or [])
        blacklisted_roles = filter_none(blacklisted_roles or [])
        bypass_roles = filter_none(bypass_roles or [])
        multiplier_roles = filter_none(multiplier_roles or {}, filter_keys=True)

        embed = cls.create_embed(
            interaction=interaction,
            config=config,
            duration=duration,
            winners=winners,
            prize=prize,
            required_roles=required_roles,
            blacklisted_roles=blacklisted_roles,
            bypass_roles=bypass_roles,
            multiplier_roles=multiplier_roles,
            messages_required=messages_required,
            allowed_message_channels=allowed_message_channels,
            amari=amari,
            weekly_amari=weekly_amari,
            donor=donor,
        )
        view = GiveawayView(config.reaction, config.participants_reaction, config.button_style)
        giveaway_message = await interaction.channel.send(config.gw_header, embed=embed, view=view)

        message_embed = discord.Embed(
            title=f"{GIFT_EMOJI} Giveaway",
            description=f"**Message・** {message}" if message else None,
            color=config.color,
        )

        if image:
            message_embed.set_image(url=image)

        extra_message = None

        if ping or image:
            ping_role = channel_config.ping if channel_config and channel_config.ping else config.ping
            extra_message = await interaction.channel.send(
                ping_role.mention if ping_role else "",
                embed=message_embed if message or image else None,  # type: ignore
                allowed_mentions=discord.AllowedMentions(roles=True),
            )

        if extra_message is None and message is not None:
            extra_message = await interaction.channel.send(embed=message_embed)

        await interaction.client.timer_cog.create_timer(
            message_id=giveaway_message.id,
            channel_id=interaction.channel.id,
            guild_id=interaction.guild.id,
            author_id=interaction.user.id,
            title="Giveaway",
            event="giveaway",
            expires=duration,
            pool=interaction.client.pool,
        )

        return await cls.create_entry(
            bot=interaction.client,
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            message_id=giveaway_message.id,
            prize=prize,
            host_id=interaction.user.id,
            donor_id=donor.id if donor else None,
            winner_count=winners,
            ends=duration,
            required_roles=[role.id for role in required_roles if role is not None] if required_roles else [],
            blacklisted_roles=[role.id for role in blacklisted_roles if role is not None] if blacklisted_roles else [],
            bypass_roles=[role.id for role in bypass_roles if role is not None] if bypass_roles else [],
            multiplier_roles={role.id: entries for role, entries in multiplier_roles.items() if role is not None}
            if multiplier_roles
            else {},
            messages={},
            messages_required=messages_required,
            allowed_message_channels=[c.id for c in allowed_message_channels] if allowed_message_channels else [],
            extra_message_id=extra_message.id if extra_message else None,
            amari=amari,
            weekly_amari=weekly_amari,
        )

    @classmethod
    async def create_entry(
        cls,
        bot: Giftify,
        guild_id: int,
        channel_id: int,
        message_id: int,
        prize: str,
        host_id: int,
        winner_count: int,
        ends: datetime.datetime,
        required_roles: List[int],
        blacklisted_roles: List[int],
        bypass_roles: List[int],
        donor_id: Optional[int],
        multiplier_roles: Optional[dict],
        messages: Optional[dict],
        messages_required: Optional[int],
        allowed_message_channels: Optional[List[int]],
        extra_message_id: Optional[int],
        amari: Optional[int],
        weekly_amari: Optional[int],
    ) -> Giveaway:
        """
        Create a new Giveaway object and insert it into the database.

        Parameters
        ----------
        bot: Giftify
            The bot instance.
        guild_id: int
            The ID of the guild (server) where the giveaway is hosted.
        channel_id: int
            The ID of the channel where the giveaway is hosted.
        message_id: int
            The ID of the message having the giveaway view.
        prize: str
            The prize of the giveaway.
        host_id: int
            The ID of the user hosting the giveaway.
        donor_id: int
            The ID of the donor of the giveaway.
        winner_count: int
            The number of winners for the giveaway.
        ends: datetime.datetime
            The time when the giveaway ends.
        required_roles: List[int]
            The list of role IDs required to participate in the giveaway.
        blacklisted_roles: List[int]
            The list of role IDs excluded from participating in the giveaway.
        bypass_roles: List[int]
            The list of user IDs exempted from giveaway restrictions.
        multiplier_roles: Optional[dict]
            A dictionary containing multiplier_roles criteria for the giveaway.
        messages: Optional[dict]
            A dictionary containing message-based criteria for the giveaway.
        messages_required: Optional[int]
            The number of messages required to participate in the giveaway.
        allowed_message_channels: Optional[int]
            The ID of the channel where the message count is tracked.
        amari: Optional[int]
            The required Amari XP to participate in the giveaway.
        weekly_amari: Optional[int]
            The required weekly Amari XP to participate in the giveaway.

        Returns
        -------
        Giveaway
            The created Giveaway object.
        """
        record = await bot.pool.fetchrow(
            "INSERT INTO giveaways (guild, channel, message, extra_message, host, donor, prize, winner_count, ends, required_roles, blacklisted_roles, bypass_roles, multiplier_roles, messages, messages_required, messages_channel, amari, weekly_amari) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18) "
            "RETURNING *",
            guild_id,
            channel_id,
            message_id,
            extra_message_id,
            host_id,
            donor_id,
            prize,
            winner_count,
            ends,
            required_roles,
            blacklisted_roles,
            bypass_roles,
            multiplier_roles,
            messages,
            messages_required,
            allowed_message_channels,
            amari,
            weekly_amari,
        )
        return cls(bot=bot, record=record)

    async def check_requirements(self, member: discord.Member) -> None:
        missing_roles = [
            role.mention
            for role_id in self.required_roles
            if (role := member.guild.get_role(role_id)) and role not in member.roles
        ]
        if missing_roles:
            msg = (
                f"You cannot join this giveaway as you are missing the following required roles: {', '.join(missing_roles)}"
            )
            raise GiveawayError(msg)

        blacklisted_roles = [
            role.mention
            for role_id in self.blacklisted_roles
            if (role := member.guild.get_role(role_id)) and role in member.roles
        ]
        if blacklisted_roles:
            msg = (
                f"You cannot join this giveaway as you have the following blacklisted roles: {', '.join(blacklisted_roles)}"
            )
            raise GiveawayError(msg)

        if self.amari and (user_level := await self.bot.fetch_level(member)) < self.amari:
            msg = f"Your amari level is less than the required level, you need `{self.amari - user_level}` more level(s) to join the giveaway."
            raise GiveawayError(msg)

        if self.weekly_amari and (weekly_exp := await self.bot.fetch_weekly_experience(member)) < self.weekly_amari:
            msg = f"Your weekly amari experience is less than the required weekly amari experience, you need `{self.weekly_amari - weekly_exp}` more experience point(s) to join the giveaway."
            raise GiveawayError(msg)

        if (
            self.messages_required
            and self.messages_required > 0
            and (user_messages := self.messages.get(member.id, 0)) < self.messages_required
        ):
            msg = f"You have sent less messages than the required messages, you need to send `{self.messages_required - user_messages}` more messages to join the giveaway."
            raise GiveawayError(msg)

    def can_bypass(self, member: discord.Member) -> bool:
        return any(member.guild.get_role(role_id) in member.roles for role_id in self.bypass_roles)

    def get_multiplier_entries(self, member: discord.Member) -> int:
        entries = 0
        for role_id, multiplier_roles_entries in self.multiplier_roles.items():
            if member.get_role(int(role_id)):
                entries += multiplier_roles_entries

        return entries or 1

    async def join(self, member: discord.Member) -> int:
        try:
            await self.check_requirements(member)
        except GiveawayError:
            if not self.can_bypass(member):
                raise

        if member.id in self.participants:
            msg = "You have already joined the giveaway."
            raise GiveawayError(msg)

        number_of_entries = self.get_multiplier_entries(member)
        entries = [member.id] * number_of_entries

        self.participants += entries

        query = """UPDATE giveaways SET participants = $1
                   WHERE guild = $2 AND channel = $3 AND message = $4
                   """

        await self.bot.pool.execute(query, self.participants, self.guild_id, self.channel_id, self.message_id)

        return len(set(self.participants))

    async def leave(self, member: discord.Member) -> int:
        if member.id not in self.participants:
            msg = "You are not a participant of this giveaway."
            raise GiveawayError(msg)

        self.participants = [participant for participant in self.participants if participant != member.id]

        query = """UPDATE giveaways SET participants = $1
                   WHERE guild = $2 AND channel = $3 AND message = $4
                   """

        await self.bot.pool.execute(query, self.participants, self.guild_id, self.channel_id, self.message_id)

        return len(set(self.participants))

    async def _mark_ended(self) -> None:
        await self.bot.pool.execute(
            "UPDATE giveaways SET ended = $1, winners = $2 WHERE guild = $3 AND channel = $4 AND message = $5",
            True,
            self.winners,
            self.guild_id,
            self.channel_id,
            self.message_id,
        )

    async def end(self) -> None:
        guild = self.bot.get_guild(self.guild_id)
        if not guild:
            return await self._mark_ended()

        config = await self.bot.fetch_config(guild)
        winners = await self.pick_winners(self.winner_count, guild)
        self.winners = [winner.id for winner in winners]

        await self._mark_ended()

        if config.dm_host:
            await self.dm_host(guild, winners, config.dm_host_message)

        if config.dm_winner:
            await self.dm_winners(config.dm_message, winners)

        channel = guild.get_channel(self.channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        gw_message = channel.get_partial_message(self.message_id)
        message = (
            safe_format(
                config.end_message,
                winners=", ".join(winner.mention for winner in winners),
                prize=bold(self.prize),
            )
            if winners
            else f"Could not pick any winners for the giveaway of {bold(self.prize)}!"
        )
        embed = self._get_end_embed(guild, config)

        view = GiveawayView(
            config.reaction,
            config.participants_reaction,
            config.button_style,
            participant_count=len(set(self.participants)),
            disabled=True,
        )

        with contextlib.suppress(discord.HTTPException):
            await gw_message.edit(content=config.gw_end_header, embed=embed, view=view)
            await gw_message.reply(message, view=self.jump_to_giveaway)

    async def reroll(self, winner_count: int) -> None:
        guild = self.bot.get_guild(self.guild_id)
        if not guild:
            return

        config = await self.bot.fetch_config(guild)
        winners = await self.pick_winners(winner_count, guild)
        self.winners = [winner.id for winner in winners]

        await self._mark_ended()

        if config.dm_winner:
            await self.dm_winners(config.dm_message, winners)

        channel = guild.get_channel(self.channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        gw_message = channel.get_partial_message(self.message_id)
        message = (
            safe_format(
                config.reroll_message,
                winners=", ".join(winner.mention for winner in winners),
                prize=bold(self.prize),
            )
            if winners
            else f"Could not pick any winners for the giveaway of {bold(self.prize)}!"
        )
        embed = self._get_end_embed(guild, config)

        view = GiveawayView(
            config.reaction,
            config.participants_reaction,
            config.button_style,
            participant_count=len(set(self.participants)),
            disabled=True,
        )

        with contextlib.suppress(discord.HTTPException):
            await gw_message.edit(content=config.gw_end_header, embed=embed, view=view)
            await gw_message.reply(message, view=self.jump_to_giveaway)

    async def cancel(self) -> None:
        await self.bot.pool.execute(
            """DELETE FROM giveaways WHERE guild = $1 AND channel = $2 AND message = $3""",
            self.guild_id,
            self.channel_id,
            self.message_id,
        )
        if self.extra_message_id is not None:
            channel = self.bot.get_channel(self.channel_id)
            if channel is not None:
                await channel.get_partial_message(self.extra_message_id).delete()  # type: ignore

    async def dm_host(self, guild: discord.Guild, winners: List[discord.Member], message: str) -> None:
        host = await self.bot.get_or_fetch_member(guild, self.host_id)
        if not host:
            return

        description = safe_format(
            message,
            winners=", ".join(winner.mention for winner in winners) if winners else "No Winners",
            prize=bold(self.prize),
        )

        embed = discord.Embed(
            title=f"Your giveaway for {self.prize} has ended!"[:256],
            description=description,
            colour=self.bot.colour,
        )
        view = self.jump_to_giveaway

        with contextlib.suppress(discord.HTTPException):
            await host.send(embed=embed, view=view)

    async def dm_winners(self, message: str, winners: List[discord.Member]) -> None:
        for winner in winners:
            description = safe_format(message, winner=winner.mention, prize=bold(self.prize))

            embed = discord.Embed(
                title="You won!",
                description=description,
                colour=self.bot.colour,
            )
            view = self.jump_to_giveaway

            with contextlib.suppress(discord.HTTPException):
                await winner.send(embed=embed, view=view)

    async def pick_winners(self, count: int, guild: discord.Guild) -> List[discord.Member]:
        winners = []

        participants = self.participants.copy()

        while count > 0 and participants:
            member_id = random.choice(participants)
            participants.remove(member_id)

            member = await self.bot.get_or_fetch_member(guild, member_id)

            if member and member not in winners:
                try:
                    await self.check_requirements(member)
                except GiveawayError:
                    if not self.can_bypass(member):
                        continue

                winners.append(member)
                count -= 1

        return winners

    def _get_end_embed(self, guild: discord.Guild, config: GuildConfig) -> discord.Embed:  # noqa: C901
        description = (
            f"This giveaway has ended!\n"
            f"Hosted By: <@!{self.host_id}>\n"
            f"Winners: {', '.join(f'<@!{winner_id}>' for winner_id in self.winners) if self.winners else 'No Winners'}\n"
            f"Ended: {discord.utils.format_dt(datetime.datetime.now(datetime.timezone.utc), style='R')} ({discord.utils.format_dt(datetime.datetime.now(datetime.timezone.utc), style='f')})\n"
        )
        if self.donor_id:
            description += f"Donor: <@!{self.donor_id}>\n"
        embed = discord.Embed(
            title=self.prize,
            description=description,
            colour=config.color,
            timestamp=self.ends,
        )
        embed.set_footer(
            text=f"{self.winner_count} winner(s) • Ended",
            icon_url=guild.icon or self.bot.user.display_avatar,
        )

        requirements = ""
        if self.required_roles:
            requirements += f"Required Roles: {', '.join(f'<@&{role_id}>' for role_id in self.required_roles)}\n"
        if self.bypass_roles:
            requirements += f"Bypass Roles: {', '.join(f'<@&{role_id}>' for role_id in self.bypass_roles)}\n"
        if self.blacklisted_roles:
            requirements += f"Blacklisted Roles: {', '.join(f'<@&{role_id}>' for role_id in self.blacklisted_roles)}\n"
        if self.messages_required:
            requirements += f"Messages Required: **{self.messages_required}** message(s) (5s cooldown)\n"
            if self.allowed_message_channels:
                requirements += f"Allowed Channels: {', '.join(f'<#{cid}>' for cid in self.allowed_message_channels)}\n"
        if self.amari:
            requirements += f"Amari Level: {self.amari}\n"
        if self.weekly_amari:
            requirements += f"Weekly Amari: {self.weekly_amari} XP Points\n"

        if requirements:
            embed.add_field(name="Requirements", value=requirements, inline=False)

        if self.multiplier_roles:
            multiplier_roles = "\n".join(
                [
                    f"- {multiplier_entries}x ・ <@&{multiplier_role}>"
                    for multiplier_role, multiplier_entries in self.multiplier_roles.items()
                ]
            )
            embed.add_field(name="Bonus Entries", value=multiplier_roles, inline=False)

        return embed


class GiveawayAction(Enum):
    START = 0
    END = 1
    REROLL = 2
    CANCEL = 3

    def __str__(self) -> str:
        if self == GiveawayAction.START:
            return "Started"
        elif self == GiveawayAction.END:
            return "Ended"
        elif self == GiveawayAction.REROLL:
            return "Rerolled"
        else:
            return "Cancelled"
            return "Cancelled"

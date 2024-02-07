from __future__ import annotations

import contextlib
import logging
from datetime import datetime
from typing import TYPE_CHECKING

import discord
import sentry_sdk
from discord import app_commands
from discord.app_commands import Transform
from discord.ext import commands

from core.bot import Giftify
from core.tree import Interaction
from models.timers import Timer
from utils.constants import TIMER_EMOJI
from utils.transformers import MessageTransformer, TimeTransformer
from utils.view import BaseView

if TYPE_CHECKING:
    from collections.abc import Generator

log = logging.getLogger("timers")


@app_commands.guild_only()
class Timers(commands.GroupCog, name="timer"):
    """A cog for starting and managing simple timers."""

    def __init__(self, bot: Giftify) -> None:
        self.bot = bot

    async def cancel_timer(self, timer: Timer) -> None:
        await self.bot.timer_cog.cancel_timer(timer)

        channel = self.bot.get_channel(timer.channel_id)
        if channel and isinstance(channel, discord.TextChannel):
            try:
                await channel.get_partial_message(timer.message_id).delete()
            except discord.HTTPException:
                pass

    @staticmethod
    def _to_chunks(user_mentions: list[str]) -> Generator[str, None, None]:
        chunk = []
        current_length = 0

        for mention in user_mentions:
            mention_length = len(mention) + 2  # Add 2 for the comma and space characters
            if current_length + mention_length > 2000:
                yield ", ".join(chunk)
                chunk = []
                current_length = 0

            chunk.append(mention)
            current_length += mention_length

        if chunk:
            yield ", ".join(chunk)

    @app_commands.command(name="start")
    @app_commands.checks.cooldown(1, 7, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.guild_only()
    @app_commands.describe(
        time="The time at which the timer will end. Must be less than 2 weeks.",
        title="The title of the timer.",
    )
    @app_commands.checks.bot_has_permissions(embed_links=True, send_messages=True, view_channel=True, add_reactions=True)
    async def timer_start(
        self,
        interaction: Interaction,
        time: Transform[datetime, TimeTransformer],
        title: app_commands.Range[str, 3, 100] = "Timer",
    ) -> None:
        """Starts a timer."""
        await interaction.response.defer(ephemeral=True)

        assert interaction.guild is not None
        if not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.client.send(interaction, "You cannot use that command in this channel type.")

        embed = discord.Embed(
            description=f"The timer will end {discord.utils.format_dt(time, style='R')} ({discord.utils.format_dt(time, style='f')})",
            color=interaction.client.colour,
            timestamp=time,
        )
        embed.set_author(
            name=f"{title}",
            icon_url=interaction.guild.icon or interaction.client.user.display_avatar,
        )
        embed.set_footer(text="Ends At")
        message = await interaction.channel.send(embed=embed)

        try:
            await message.add_reaction(TIMER_EMOJI)
        except discord.HTTPException:
            pass

        await self.bot.timer_cog.create_timer(
            message.id,
            interaction.channel.id,
            interaction.guild.id,
            interaction.user.id,
            title,
            "timer",
            time,
            interaction.client.pool,
        )

        await interaction.client.send(interaction, "Timer successfully started!")

    @app_commands.command(name="end")
    @app_commands.checks.cooldown(1, 7, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.guild_only()
    @app_commands.describe(
        message="The ID of the timer message.",
    )
    async def timer_end(
        self,
        interaction: Interaction,
        message: Transform[discord.PartialMessage, MessageTransformer],
    ) -> None:
        """Ends a timer."""
        await interaction.response.defer(ephemeral=True)

        assert message.guild is not None

        timer = await self.bot.timer_cog.get_timer(
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            message_id=message.id,
        )
        if not timer or timer.event != "timer":
            return await interaction.client.send(interaction, "That is not a valid timer message.", "warn")

        if timer.author_id != interaction.user.id:
            return await interaction.client.send(interaction, "That is not your timer message.", "warn")
        await self.bot.timer_cog.call_timer(timer, manually=True)
        await interaction.client.send(interaction, "Timer successfully ended!")

    @app_commands.command(name="cancel")
    @app_commands.checks.cooldown(1, 7, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.guild_only()
    @app_commands.describe(
        message="The ID of the timer message.",
    )
    async def timer_cancel(
        self,
        interaction: Interaction,
        message: Transform[discord.PartialMessage, MessageTransformer],
    ) -> None:
        """Cancels a timer."""
        await interaction.response.defer(ephemeral=True)

        assert message.guild is not None

        timer = await self.bot.timer_cog.get_timer(
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            message_id=message.id,
        )
        if not timer or timer.event != "timer":
            return await interaction.client.send(interaction, "That is not a valid timer message.", "warn")

        if timer.author_id != interaction.user.id:
            return await interaction.client.send(interaction, "That is not your timer message.", "warn")

        await self.cancel_timer(timer)

        await interaction.client.send(interaction, "Timer successfully cancelled!")

    @commands.Cog.listener()
    async def on_timer_end(self, timer: Timer) -> None:
        channel = self.bot.get_channel(timer.channel_id)

        if channel and isinstance(channel, discord.TextChannel):
            try:
                message = await channel.fetch_message(timer.message_id)

            except Exception as error:
                if not isinstance(error, discord.HTTPException):
                    sentry_sdk.capture_exception(error)
                    log.error("Ignoring exception in call timer function", exc_info=error)
            else:
                expired_at = discord.utils.utcnow()

                embed = discord.Embed(
                    description=f"The timer ended {discord.utils.format_dt(expired_at, style='R')} ({discord.utils.format_dt(expired_at, style='f')})",
                    color=self.bot.colour,
                    timestamp=expired_at,
                )

                embed.description = f"The timer ended {discord.utils.format_dt(expired_at, style='R')} ({discord.utils.format_dt(expired_at, style='f')})"

                embed.set_author(
                    name=f"{timer.title} (Ended)",
                    icon_url=channel.guild.icon or self.bot.user.display_avatar,
                )
                embed.set_footer(text="Ended At")
                with contextlib.suppress(discord.HTTPException):
                    await message.edit(embed=embed)
                    view = BaseView()
                    view.add_item(discord.ui.Button(label="Jump To Message", url=message.jump_url))
                    await message.reply(f"The timer for **{timer.title}** has ended.", view=view)
                if timer_reactions := [reaction for reaction in message.reactions if str(reaction.emoji) == TIMER_EMOJI]:
                    mentions = [user.mention async for user in timer_reactions[0].users() if not user.bot]

                    for chunk in self._to_chunks(mentions):
                        with contextlib.suppress(discord.HTTPException):
                            await channel.send(
                                chunk,
                                delete_after=3,
                                allowed_mentions=discord.AllowedMentions(users=True),
                            )


async def setup(bot: Giftify) -> None:
    await bot.add_cog(Timers(bot))

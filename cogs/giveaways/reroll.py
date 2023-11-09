import datetime

import discord
from discord import app_commands
from discord.app_commands import Transform
from discord.ext import commands

from bot import Giftify
from models.giveaways import Giveaway, GiveawayAction
from utils.transformers import MessageTransformer
from utils.tree import Interaction


class GiveawayReroll(commands.GroupCog):
    """A cog for rerolling giveaways."""

    bot: Giftify

    @app_commands.command(name="reroll")
    @app_commands.describe(
        message="The ID of the giveaway message or the message URL.",
        winners="The number of winners.",
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def giveaway_reroll(
        self,
        interaction: Interaction,
        message: Transform[discord.PartialMessage, MessageTransformer],
        winners: int,
    ):
        """Reroll the winners of a giveaway."""

        await interaction.response.defer(ephemeral=True)

        assert message.guild is not None
        assert isinstance(interaction.user, discord.Member)

        giveaway = await self.bot.fetch_giveaway(
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            message_id=message.id,
        )
        if giveaway is None:
            return await interaction.client.send(
                interaction,
                "That is not a valid giveaway message.",
                reason="warn",
            )
        if not giveaway.ended:
            return await interaction.client.send(
                interaction, "You cannot end a running giveaway."
            )

        if giveaway.host_id != interaction.user.id:
            if not interaction.user.guild_permissions.manage_guild:
                return await interaction.client.send(
                    interaction,
                    "You cannot reroll that giveaway because you are not the host of that giveaway.",
                    reason="error",
                )

        self.bot.dispatch(
            "giveaway_action", GiveawayAction.REROLL, giveaway, interaction.user
        )
        await giveaway.reroll(winners)

        await interaction.client.send(
            interaction, "Successfully rerolled the giveaway!"
        )

import discord
from discord import app_commands
from discord.app_commands import Transform
from discord.ext import commands

from bot import Giftify
from models.giveaways import GiveawayAction
from utils.transformers import MessageTransformer
from utils.tree import Interaction


class GiveawayEnd(commands.GroupCog):
    """A cog for ending giveaways."""

    bot: Giftify

    @app_commands.command(name="end")
    @app_commands.describe(
        message="The ID of the giveaway message or the message URL.",
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def giveaway_end(
        self,
        interaction: Interaction,
        message: Transform[discord.PartialMessage, MessageTransformer],
    ):
        """End a running giveaway before its expiration time."""
        assert message.guild is not None

        await interaction.response.defer(ephemeral=True)

        giveaway = await self.bot.fetch_giveaway(
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            message_id=message.id,
        )
        if not giveaway:
            return await interaction.client.send(
                interaction,
                "That is not a valid giveaway message. If that giveaway has already ended, you can't end it again.",
                reason="warn",
            )
        self.bot.dispatch(
            "giveaway_action", GiveawayAction.END, giveaway, interaction.user
        )

        if timer := await self.bot.timer_cog.get_timer(
            guild_id=giveaway.guild_id,
            channel_id=giveaway.channel_id,
            message_id=giveaway.message_id,
        ):
            await self.bot.timer_cog.call_timer(timer, manually=True)
        else:
            return await interaction.client.send(
                interaction, "The timer associated with that message was not found!"
            )

        await interaction.client.send(interaction, "Successfully ended the giveaway!")

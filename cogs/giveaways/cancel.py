import discord
from discord import app_commands
from discord.app_commands import Transform
from discord.ext import commands

from core.bot import Giftify
from core.tree import Interaction
from models.giveaways import GiveawayAction
from utils.transformers import MessageTransformer


class GiveawayCancel(commands.GroupCog):
    """A cog for cancelling giveaways."""

    bot: Giftify

    @app_commands.command(name="cancel")
    @app_commands.describe(
        message="The ID of the giveaway message or the message URL.",
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def giveaway_cancel(
        self,
        interaction: Interaction,
        message: Transform[discord.PartialMessage, MessageTransformer],
    ):
        """Cancel a running giveaway."""

        await interaction.response.defer(ephemeral=True)

        assert message.guild is not None

        giveaway = await self.bot.fetch_giveaway(
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            message_id=message.id,
        )
        if giveaway is None:
            return await interaction.client.send(
                interaction,
                "That is not a valid giveaway message. If a giveaway has already ended, you cannot cancel it.",
                reason="warn",
            )

        self.bot.dispatch(
            "giveaway_action", GiveawayAction.CANCEL, giveaway, interaction.user
        )
        await giveaway.cancel()
        if timer := await self.bot.timer_cog.get_timer(
            guild_id=giveaway.guild_id,
            channel_id=giveaway.channel_id,
            message_id=giveaway.message_id,
        ):
            await self.bot.timer_cog.cancel_timer(timer)

        try:
            await message.delete()
        except discord.HTTPException:
            pass

        await interaction.client.send(
            interaction, "Successfully cancelled the giveaway!"
        )

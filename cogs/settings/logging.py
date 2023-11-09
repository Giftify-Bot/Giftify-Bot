import discord
from discord import app_commands
from discord.ext import commands

from utils.tree import Interaction


class GiveawayLogging(commands.GroupCog):
    """Set the logging channel for giveaways."""

    @app_commands.command(name="logging")
    @app_commands.describe(channel="The channel to log giveaway actions in.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    @app_commands.checks.bot_has_permissions(manage_webhooks=True)
    async def logging(self, interaction: Interaction, channel: discord.TextChannel):
        """Set the logging channel for giveaways."""

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)

        try:
            await interaction.client.get_webhook(channel)
        except discord.HTTPException:
            return await interaction.client.send(
                interaction,
                "Failed to create a webhook! Make sure to check my permissions.",
                "warn",
            )

        await config.update("logging", channel, interaction.client.pool)

        message = f"Successfully set giveaway logging channel to {channel.mention!r}"

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

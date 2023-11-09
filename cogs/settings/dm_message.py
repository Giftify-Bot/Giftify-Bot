import discord
from discord import app_commands
from discord.app_commands import Range
from discord.ext import commands

from utils.tree import Interaction


def is_valid_message(message: str) -> bool:
    return "{winner}" and "{prize}" in message


class GiveawayDMMessage(commands.GroupCog):
    """Edit the giveaway DM message."""

    @app_commands.command(name="dm_message")
    @app_commands.describe(message="The message to send to the winner when a giveaway ends.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def dm_message(self, interaction: Interaction, message: Range[str, 15, 255]):
        """Customize the giveaway winner direct message."""

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)

        if not is_valid_message(message):
            return await interaction.client.send(
                interaction,
                "You must use the `{winner}` and `{prize}` variables.",
                reason="warn",
            )

        await config.update("dm_message", message, interaction.client.pool)

        await interaction.client.send(
            interaction,
            f"Successfully set the giveaway winner direct message to {message!r}",
            "success",
        )

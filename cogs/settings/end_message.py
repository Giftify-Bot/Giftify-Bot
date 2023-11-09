import discord
from discord import app_commands
from discord.app_commands import Range
from discord.ext import commands

from utils.tree import Interaction


def is_valid_message(message: str) -> bool:
    if "{winners}" and "{prize}" in message:
        return True
    else:
        return False


class GiveawayEndMessage(commands.GroupCog):
    """Edit the giveaway end message."""

    @app_commands.command(name="end_message")
    @app_commands.describe(message="The message to send when a giveaway ends.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def end_message(self, interaction: Interaction, message: Range[str, 15, 255]):
        """Customize the giveaway end message."""

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)

        if not is_valid_message(message):
            return await interaction.client.send(
                interaction,
                "You must use the `{winners}` and `{prize}` variables.",
                reason="warn",
            )

        await config.update("end_message", message, interaction.client.pool)

        await interaction.client.send(
            interaction,
            f"Successfully set the giveaway end message to {message!r}",
            "success",
        )

import discord
from discord import app_commands
from discord.app_commands import Range
from discord.ext import commands

from utils.tree import Interaction


def is_valid_message(message: str) -> bool:
    return "{winners}" and "{prize}" in message


class GiveawayRerollMessage(commands.GroupCog):
    """Edit the giveaway reroll message."""

    @app_commands.command(name="reroll_message")
    @app_commands.describe(message="The message to send when a giveaway rerolls.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def reroll_message(self, interaction: Interaction, message: Range[str, 15, 255]):
        """Customize the giveaway reroll message."""

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

        await config.update("reroll_message", message, interaction.client.pool)

        await interaction.client.send(
            interaction,
            f"Successfully set the giveaway reroll message to {message!r}",
            "success",
        )

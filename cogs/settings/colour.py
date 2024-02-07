import discord
from discord import app_commands
from discord.app_commands import Transform
from discord.ext import commands

from core.tree import Interaction
from utils.transformers import ColourTransformer


class GiveawayEmbedColour(commands.GroupCog):
    """Toggle embed colour"""

    @app_commands.command(name="colour")
    @app_commands.describe(colour="The colour, must be a hexadecimal number.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def colour(
        self, interaction: Interaction, colour: Transform[int, ColourTransformer]
    ):
        """Set colour of giveaway embed."""

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)
        await config.update("color", colour, interaction.client.pool)

        message = f"Successfully set embed colour to `{str(discord.Colour(colour))}`"

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

from enum import Enum

import discord
from discord import app_commands
from discord.ext import commands

from core.tree import Interaction


class ButtonStyle(Enum):
    Blurple = discord.ButtonStyle.blurple
    Grey = discord.ButtonStyle.grey
    Green = discord.ButtonStyle.green
    Red = discord.ButtonStyle.red


class GiveawayButtonColour(commands.GroupCog):
    """Toggle button colour"""

    @app_commands.command(name="button_colour")
    @app_commands.describe(colour="Choose the button style.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def button_colour(self, interaction: Interaction, colour: ButtonStyle):
        """Set colour of giveaway button."""

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)
        await config.update("button_style", colour.value, interaction.client.pool)

        message = f"Successfully set giveaway button colour to `{colour.name}`"

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

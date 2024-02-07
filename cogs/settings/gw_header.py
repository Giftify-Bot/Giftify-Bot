import discord
from discord import app_commands
from discord.app_commands import Range
from discord.ext import commands

from core.tree import Interaction


class GiveawayHeader(commands.GroupCog):
    """Customize the giveaway embed header."""

    @app_commands.command(name="header")
    @app_commands.describe(header="The embed header for giveaways.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def gw_header(self, interaction: Interaction, header: Range[str, 5, 100]):
        """Customize the giveaway embed header."""

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)

        await config.update("gw_header", header, interaction.client.pool)

        await interaction.client.send(
            interaction,
            f"Successfully set the giveaway embed header to {header!r}",
            "success",
        )

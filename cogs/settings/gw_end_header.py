import discord
from discord import app_commands
from discord.app_commands import Range
from discord.ext import commands

from utils.tree import Interaction


class GiveawayEndHeader(commands.GroupCog):
    """Customize the giveaway end embed header."""

    @app_commands.command(name="end_header")
    @app_commands.describe(header="The embed header for ended giveaways.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def gw_end_header(self, interaction: Interaction, header: Range[str, 5, 100]):
        """Customize the giveaway end embed header."""

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)

        await config.update("gw_end_header", header, interaction.client.pool)

        await interaction.client.send(
            interaction,
            f"Successfully set the giveaway embed header to {header!r}",
            "success",
        )

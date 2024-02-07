import discord
from discord import app_commands
from discord.ext import commands

from core.tree import Interaction


class GiveawayDMHost(commands.GroupCog):
    """Toggle the giveaway hosts dm."""

    @app_commands.command(name="dm_host")
    @app_commands.describe(toggle="Wheter dm the giveaway hosts or not.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def dm_host(self, interaction: Interaction, toggle: bool):
        """Toggle the giveaway hosts dm."""

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)

        await config.update("dm_host", toggle, interaction.client.pool)

        message = (
            "I will now dm the hosts!"
            if toggle
            else "I will not dm the hosts from now on!"
        )

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

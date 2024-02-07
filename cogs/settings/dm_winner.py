import discord
from discord import app_commands
from discord.ext import commands

from core.tree import Interaction


class GiveawayDMWinner(commands.GroupCog):
    """Toggle the giveaway winners dm."""

    @app_commands.command(name="dm_winner")
    @app_commands.describe(toggle="Wheter dm the giveaway winners or not.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def dm_winner(self, interaction: Interaction, toggle: bool):
        """Toggle the giveaway winners dm."""

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)

        await config.update("dm_winner", toggle, interaction.client.pool)

        message = (
            "I will now dm the winners!"
            if toggle
            else "I will not dm the winners from now on!"
        )

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

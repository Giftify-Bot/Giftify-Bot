import discord
from discord import app_commands
from discord.ext import commands

from core.tree import Interaction


class GiveawayPing(commands.GroupCog):
    """Set the ping role for giveaways."""

    @app_commands.command(name="ping")
    @app_commands.describe(role="The role to mention when a giveaway starts.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def ping(self, interaction: Interaction, role: discord.Role):
        """Set the ping role for giveaways."""

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)

        if role.id == interaction.guild.id:
            return await interaction.client.send(
                interaction, "You can't set @everyone role as the ping role."
            )

        config = await interaction.client.fetch_config(interaction.guild)
        await config.update("ping", role, interaction.client.pool)

        message = f"Successfully set giveaway ping role to {role.mention!r}"
        await interaction.client.send(
            interaction,
            message,
            "success",
        )

import discord
from discord import app_commands
from discord.ext import commands

from utils.tree import Interaction


class GiveawayManagers(commands.GroupCog):
    """Set the managers role."""

    manager = app_commands.Group(
        name="manager", description="Manage the giveaways.", guild_only=True
    )

    @manager.command(name="add")
    @app_commands.describe(role="Mention a role or enter a role ID.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def manager_add(self, interaction: Interaction, role: discord.Role):
        """Set the role which can manage giveaways."""

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)

        managers = config.managers
        if len(managers) >= 5:
            return await interaction.client.send(
                interaction, "You cannot add more than `5` managers.", reason="warn"
            )
        if role in managers:
            return await interaction.client.send(
                interaction,
                "That role is already added as a manager role.",
                reason="warn",
            )

        managers.append(role)
        await config.update("managers", managers, interaction.client.pool)

        message = f"Successfully added {role.mention!r} to manager roles."

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

    @manager.command(name="remove")
    @app_commands.describe(role="Mention a role or enter a role ID.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def manager_remove(self, interaction: Interaction, role: discord.Role):
        """Deny the role's permissions to manage giveaways."""

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)

        managers = config.managers
        if not role in managers:
            return await interaction.client.send(
                interaction, "That role is not set as a manager role.", reason="warn"
            )
        managers.remove(role)
        await config.update("managers", managers, interaction.client.pool)

        message = f"Successfully removed {role.mention!r} from manager roles."

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

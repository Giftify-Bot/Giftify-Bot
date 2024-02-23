import discord
from discord import app_commands
from discord.ext import commands

from core.tree import Interaction


class GiveawayDefaults(commands.GroupCog):
    """Edit the default giveaway settings."""

    defaults = app_commands.Group(
        name="defaults",
        description="Edit the default giveaway settings.",
        guild_only=True,
    )

    @defaults.command(name="add_requirement")
    @app_commands.describe(role="Mention a role or enter a role ID.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def defaults_add_requirement(self, interaction: Interaction, role: discord.Role) -> None:
        """Add a default requirement role."""
        assert interaction.guild is not None
        if role.id == interaction.guild.id:
            await interaction.client.send(
                interaction,
                "You can't set `@everyone` role as giveaway requirement.",
                reason="warn",
            )

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)

        required_roles = config.required_roles
        if len(required_roles) >= 5:
            return await interaction.client.send(
                interaction,
                "You cannot add more than `5` default requirements.",
                reason="warn",
            )
        if role in required_roles:
            return await interaction.client.send(
                interaction,
                "That role is already added as a default requirement role.",
                reason="warn",
            )

        required_roles.append(role)
        await config.update("required_roles", required_roles, interaction.client.pool)

        message = f"Successfully added {role.mention!r} to default requirements roles."

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

    @defaults.command(name="remove_requirement")
    @app_commands.describe(role="Mention a role or enter a role ID.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def defaults_remove_requirement(self, interaction: Interaction, role: discord.Role) -> None:
        """Remove a default requirement role."""

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)

        required_roles = config.required_roles
        if role not in required_roles:
            return await interaction.client.send(
                interaction,
                "That role is not set as a default requirement role.",
                reason="warn",
            )
        required_roles.remove(role)
        await config.update("required_roles", required_roles, interaction.client.pool)

        message = f"Successfully removed {role.mention!r} from default requirement roles."

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

    @defaults.command(name="add_blacklist")
    @app_commands.describe(role="Mention a role or enter a role ID.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def defaults_add_blacklist(self, interaction: Interaction, role: discord.Role) -> None:
        """Add a default blacklist role."""
        assert interaction.guild is not None

        if role.id == interaction.guild.id:
            await interaction.client.send(
                interaction,
                "You can't set `@everyone` role as giveaway blacklist.",
                reason="warn",
            )

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)

        blacklisted_roles = config.blacklisted_roles
        if len(blacklisted_roles) >= 5:
            return await interaction.client.send(
                interaction,
                "You cannot add more than `5` default blacklist role.",
                reason="warn",
            )
        if role in blacklisted_roles:
            return await interaction.client.send(
                interaction,
                "That role is already added as a default blacklist role.",
                reason="warn",
            )

        blacklisted_roles.append(role)
        await config.update("blacklisted_roles", blacklisted_roles, interaction.client.pool)

        message = f"Successfully added {role.mention!r} to default blacklist roles."

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

    @defaults.command(name="remove_blacklist")
    @app_commands.describe(role="Mention a role or enter a role ID.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def defaults_remove_blacklist(self, interaction: Interaction, role: discord.Role) -> None:
        """Remove a default blacklist role."""

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)

        blacklisted_roles = config.blacklisted_roles
        if role not in blacklisted_roles:
            return await interaction.client.send(
                interaction,
                "That role is not set as a default blacklist role.",
                reason="warn",
            )
        blacklisted_roles.remove(role)
        await config.update("blacklisted_roles", blacklisted_roles, interaction.client.pool)

        message = f"Successfully removed {role.mention!r} from default blacklist roles."

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

    @defaults.command(name="add_bypass_roles")
    @app_commands.describe(role="Mention a role or enter a role ID.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def defaults_add_bypass_roles(self, interaction: Interaction, role: discord.Role) -> None:
        """Add a default bypass role."""
        assert interaction.guild is not None
        if role.id == interaction.guild.id:
            await interaction.client.send(
                interaction,
                "You can't set `@everyone` role as giveaway bypass role.",
                reason="warn",
            )

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)

        bypass_roles = config.bypass_roles
        if len(bypass_roles) >= 5:
            return await interaction.client.send(
                interaction,
                "You cannot add more than `5` default bypass role.",
                reason="warn",
            )
        if role in bypass_roles:
            return await interaction.client.send(
                interaction,
                "That role is already added as a default bypass role.",
                reason="warn",
            )

        bypass_roles.append(role)
        await config.update("bypass_roles", bypass_roles, interaction.client.pool)

        message = f"Successfully added {role.mention!r} to default bypass roles."

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

    @defaults.command(name="remove_bypass_roles")
    @app_commands.describe(role="Mention a role or enter a role ID.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def defaults_remove_bypass_roles(self, interaction: Interaction, role: discord.Role) -> None:
        """Remove a default bypass role."""

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)

        bypass_roles = config.bypass_roles
        if role not in bypass_roles:
            return await interaction.client.send(
                interaction,
                "That role is not set as a default bypass role.",
                reason="warn",
            )
        bypass_roles.remove(role)
        await config.update("bypass_roles", bypass_roles, interaction.client.pool)

        message = f"Successfully removed {role.mention!r} from default bypass roles."

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

    @defaults.command(name="multiplier_entries")
    @app_commands.describe(
        role="Mention a role or enter a role ID.",
        entries="The number of multiplier entries for the role. Enter 1 to reset.",
    )
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def defaults_multiplier_entries(
        self,
        interaction: Interaction,
        role: discord.Role,
        entries: app_commands.Range[int, 1, 5],
    ) -> None:
        """Edit multiplier entries of a role."""
        assert interaction.guild is not None
        if role.id == interaction.guild.id:
            await interaction.client.send(
                interaction,
                "You can't add multiplier entries to `@everyone` role.",
                reason="warn",
            )

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)

        multiplier_roles = config.multiplier_roles
        if len(multiplier_roles) >= 5:
            return await interaction.client.send(
                interaction,
                "You cannot add more than `5` default multiplier entry roles.",
                reason="warn",
            )
        if entries == 1:
            if role in multiplier_roles:
                multiplier_roles.pop(role)
            else:
                return await interaction.client.send(
                    interaction,
                    "That role doesn't have any default extra multiplier entries.",
                    reason="warn",
                )
        else:
            multiplier_roles[role] = entries
        await config.update("multiplier_roles", multiplier_roles, interaction.client.pool)

        message = f"Successfully set {role.mention}'s multiplier entries to `{entries}`."

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

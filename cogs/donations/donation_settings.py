from typing import List

import discord
from discord import app_commands
from discord.app_commands import Range, Transform
from discord.ext import commands

from bot import Giftify
from models.donation_settings import GuildDonationConfig
from utils.transformers import DonationCategoryTransformer
from utils.tree import Interaction


class DonationSettings(commands.GroupCog):
    """Cog for managing donation settings."""

    bot: Giftify

    settings = app_commands.Group(
        name="settings", description="Manage the donation config.", guild_only=True
    )

    @settings.command(name="add_manager")
    @app_commands.describe(
        category="The name of the donation category.",
        role="The role to give the manage donation permissions.",
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    @app_commands.checks.has_permissions(manage_guild=True)
    async def donation_settings_add_manager(
        self,
        interaction: Interaction,
        category: Transform[GuildDonationConfig, DonationCategoryTransformer],
        role: discord.Role,
    ):
        """Set the role which can manage donations."""
        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)

        managers = category.managers
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
        await category.update("managers", managers)

        message = f"Successfully added {role.mention!r} to manager roles."

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

    @settings.command(name="remove_manager")
    @app_commands.describe(
        category="The name of the donation category.",
        role="The role to deny the manage donation permissions.",
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    @app_commands.checks.has_permissions(manage_guild=True)
    async def donation_settings_remove_manager(
        self,
        interaction: Interaction,
        category: Transform[GuildDonationConfig, DonationCategoryTransformer],
        role: discord.Role,
    ):
        """Deny the role's permissions to manage donations."""
        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)

        managers = category.managers
        if not role in managers:
            return await interaction.client.send(
                interaction, "That role is not set as a manager role.", reason="warn"
            )
        managers.remove(role)
        await category.update("managers", managers)

        message = f"Successfully removed {role.mention!r} from manager roles."

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

    @settings.command(name="list_manager")
    @app_commands.describe(category="The name of the donation category.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    @app_commands.checks.has_permissions(manage_guild=True)
    async def donation_settings_list_manager(
        self,
        interaction: Interaction,
        category: Transform[GuildDonationConfig, DonationCategoryTransformer],
    ):
        """Show the roles having manage donation permissions."""
        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)

        embed = discord.Embed(
            title=f"The donation managers of {category.category}",
            description=", ".join(role.mention for role in category.managers),
            colour=self.bot.colour,
        )
        await interaction.followup.send(
            embed=embed,
        )

    @settings.command(name="logging")
    @app_commands.describe(
        category="The name of the donation category.",
        channel="The channel to log the donation events.",
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    @app_commands.checks.has_permissions(manage_guild=True)
    async def donation_settings_logging(
        self,
        interaction: Interaction,
        category: Transform[GuildDonationConfig, DonationCategoryTransformer],
        channel: discord.TextChannel,
    ):
        """Set the channel to log donation events."""
        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)

        try:
            await interaction.client.get_webhook(channel)
        except discord.HTTPException:
            return await interaction.client.send(
                interaction,
                "Failed to create a webhook! Make sure to check my permissions.",
                "warn",
            )

        await category.update("logging", channel)

        message = f"Successfully set donation logging channel to {channel.mention!r}"

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

    @settings.command(name="symbol")
    @app_commands.describe(
        category="The name of the donation category.",
        symbol="The symbol of donation category.",
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    @app_commands.checks.has_permissions(manage_guild=True)
    async def donation_settings_symbol(
        self,
        interaction: Interaction,
        category: Transform[GuildDonationConfig, DonationCategoryTransformer],
        symbol: Range[str, 1, 1],
    ):
        """Set the channel to log donation events."""
        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)

        await category.update("symbol", symbol)

        message = f"Successfully set donations symbol for {category} to {symbol!r}."

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

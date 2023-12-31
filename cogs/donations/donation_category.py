import datetime

import discord
from discord import app_commands
from discord.app_commands import Range, Transform
from discord.ext import commands

from bot import Giftify
from models.donation_settings import GuildDonationConfig
from utils.transformers import DonationCategoryTransformer
from utils.tree import Interaction


class DonationCategory(commands.GroupCog):
    """Cog for creating/deleting donation category."""

    bot: Giftify

    category_command = app_commands.Group(
        name="category",
        description="Commands for creating or deleting donation categories.",
        guild_only=True,
    )

    @category_command.command(name="create")
    @app_commands.describe(
        category="The unique name of the donation category.",
        symbol="The symbol to represent the category.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def donation_category_create(
        self,
        interaction: Interaction,
        category: Range[str, 3, 50],
        symbol: Range[str, 1, 1] = "$",
    ) -> None:
        """The command to create a new donation category."""
        await interaction.response.defer()
        assert interaction.guild is not None

        config = self.bot.get_donation_config(interaction.guild, category)
        if config:
            return await interaction.client.send(
                interaction,
                f"The donation category of name {category} already exists!",
                "warn",
            )

        if len(self.bot.get_guild_donation_categories(interaction.guild)) >= 25:
            return await interaction.client.send(
                interaction,
                "You cannot create more than `25` donation categories.",
                "warn",
            )

        config = await GuildDonationConfig.create(
            interaction.guild.id, category, self.bot, symbol=symbol
        )

        self.bot.donation_configs.append(config)

        await interaction.client.send(
            interaction,
            f"Successfully created the donation category of name {category} and symbol {symbol}!",
        )

    @category_command.command(name="delete")
    @app_commands.describe(category="The unique name of the donation category.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 25, key=lambda i: (i.guild, i.user.id))
    async def donation_category_delete(
        self,
        interaction: Interaction,
        category: Transform[GuildDonationConfig, DonationCategoryTransformer],
    ) -> None:
        """The command to delete an existing donation category."""
        await interaction.response.defer()
        assert interaction.guild is not None

        prompt = await interaction.client.prompt(
            f"Are you sure you want to delete the donation category {category.category}?",
            interaction=interaction,
            success_message=f"Successfully deleted the donation category of name {category.category}!",
            cancel_message="Alright, not deleting this time!",
        )

        if prompt:
            self.bot.donation_configs.remove(category)
            await category.delete()

    @category_command.command(name="reset")
    @app_commands.describe(category="The unique name of the donation category.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 25, key=lambda i: (i.guild, i.user.id))
    async def donation_category_reset(
        self,
        interaction: Interaction,
        category: Transform[GuildDonationConfig, DonationCategoryTransformer],
    ) -> None:
        """The command to reset all the donations of a donation category."""
        await interaction.response.defer()
        assert interaction.guild is not None

        prompt = await interaction.client.prompt(
            f"Are you sure you want to reset all the donations of donation category {category.category}?",
            interaction=interaction,
            success_message=f"Successfully reset all the donations of donation category {category.category}!",
            cancel_message="Alright, not resetting this time!",
        )

        if prompt:
            await category.reset()

    @category_command.command(name="rename")
    @app_commands.describe(
        category="The unique name of the donation category.",
        name="The new name for the category.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def donation_category_rename(
        self,
        interaction: Interaction,
        category: Transform[GuildDonationConfig, DonationCategoryTransformer],
        name: Range[str, 1, 50],
    ) -> None:
        """The command to rename a donation category."""
        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)

        await category.update("category", name)

        message = f"Successfully renamed that donation category to {name!r}."

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

    @category_command.command(name="list")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def donation_category_list(
        self,
        interaction: Interaction,
    ) -> None:
        """The command to check the list of donation categories."""
        await interaction.response.defer()
        assert interaction.guild is not None

        categories = self.bot.get_guild_donation_categories(interaction.guild)
        if categories:
            embed = discord.Embed(
                title=f"The donation categories of guild {interaction.guild.name}",
                description=", ".join(f"`{category}`" for category in categories),
                color=self.bot.colour,
                timestamp=datetime.datetime.now(),
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.client.send(
                interaction,
                "This guild has no donation categories",
                "warn",
            )

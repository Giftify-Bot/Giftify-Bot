from typing import List, Tuple

import discord
from discord import app_commands
from discord.app_commands import Transform
from discord.ext import commands

from bot import Giftify
from models.donation_settings import GuildDonationConfig
from utils.paginator import BaseButtonPaginator
from utils.transformers import AmountTransformer, DonationCategoryTransformer
from utils.tree import Interaction


class RolesPaginator(BaseButtonPaginator[Tuple[int, discord.Role]]):
    async def format_page(
        self, roles: List[Tuple[int, discord.Role]], /
    ) -> discord.Embed:
        assert self.bot is not None

        description = "The donation autoroles of this server are:\n\n"

        for i, (amount, role) in enumerate(roles):
            description += f"`{i + 1}.` {role.mention} - **{amount:,}**.\n"

        embed = discord.Embed(
            title="Donation Autoroles",
            description=description,
            color=self.bot.colour,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar)

        embed.set_footer(text=f"Page {self.current_page}/{self.total_pages}")

        return embed


class DonationAutorole(commands.GroupCog):
    """Cog for managing donation autoroles."""

    bot: Giftify

    autorole = app_commands.Group(
        name="autorole",
        description="Commands for managing donation autoroles.",
        guild_only=True,
    )

    @autorole.command(name="set")
    @app_commands.describe(
        category="The name of the donation category.",
        amount="The amount required to get the auto role.",
        role="The role to add on reaching specified amount of donations.",
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    @app_commands.checks.has_permissions(manage_guild=True)
    async def donation_autorole_set(
        self,
        interaction: Interaction,
        category: Transform[GuildDonationConfig, DonationCategoryTransformer],
        amount: Transform[int, AmountTransformer],
        role: discord.Role,
    ) -> None:
        """The command to set donation autorole for some amount."""
        await interaction.response.defer()

        assert interaction.guild is not None
        assert isinstance(interaction.user, discord.Member)

        if role >= interaction.guild.me.top_role:
            return await interaction.client.send(
                interaction,
                f"The role {role.mention} is higher than my highest role {interaction.guild.me.top_role.mention}!",
                "warn",
            )
        if role >= interaction.user.top_role:
            if interaction.user.id != interaction.guild.owner_id:
                return await interaction.client.send(
                    interaction,
                    f"The role {role.mention} is higher than your highest role {interaction.user.top_role.mention}!",
                    "warn",
                )

        if not role.is_assignable():
            return await interaction.client.send(
                interaction,
                f"The role {role.mention} cannot be assigned manually!",
                "warn",
            )

        roles = category.roles
        roles[amount] = role

        await category.update("roles", roles)

        await interaction.client.send(
            interaction,
            f"Successfully updated the role of amount **{category.symbol} {amount:,}** to be {role.mention!r}.",
        )

    @autorole.command(name="reset")
    @app_commands.describe(
        category="The name of the donation category.",
        amount="The amount to reset.",
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    @app_commands.checks.has_permissions(manage_guild=True)
    async def donation_autorole_reset(
        self,
        interaction: Interaction,
        category: Transform[GuildDonationConfig, DonationCategoryTransformer],
        amount: Transform[int, AmountTransformer],
    ) -> None:
        """The command to reset donation autorole for some amount."""
        await interaction.response.defer()

        assert interaction.guild is not None
        assert isinstance(interaction.user, discord.Member)

        roles = category.roles
        if amount not in roles:
            return await interaction.client.send(
                interaction=interaction,
                message="No donation autorole set for that amount.",
            )
        del roles[amount]

        await category.update("roles", roles)

        await interaction.client.send(
            interaction,
            f"Successfully reset the donation role of amount **{category.symbol} {amount:,}**.",
        )

    @autorole.command(name="list")
    @app_commands.describe(category="The name of the donation category.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    @app_commands.checks.has_permissions(manage_guild=True)
    async def donation_autorole_list(
        self,
        interaction: Interaction,
        category: Transform[GuildDonationConfig, DonationCategoryTransformer],
    ) -> None:
        """The command to set donation autorole for some amount."""
        await interaction.response.defer()
        assert interaction.guild is not None

        if category.roles:
            view = RolesPaginator(
                entries=list(category.roles.items()), per_page=10, target=interaction
            )
            embed = await view.embed()
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.client.send(
                interaction,
                "There aren't any donation autoroles setup for that category.",
                "warn",
            )

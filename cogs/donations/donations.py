from __future__ import annotations

import datetime
from typing import List, Optional, Tuple

import asyncpg
import discord
from discord import app_commands
from discord.app_commands import Transform
from discord.ext import commands

from bot import Giftify
from models.donation_settings import DonationAction, GuildDonationConfig
from utils.constants import (
    DONATE_EMOJI,
    MINUS_EMOJI,
    MONEY_EMOJI,
    PLUS_EMOJI,
    SUCCESS_EMOJI,
)
from utils.exceptions import (
    DonationCategoryError,
    DonationError,
    DonationPermissionsError,
)
from utils.paginator import BaseButtonPaginator
from utils.transformers import AmountTransformer, DonationCategoryTransformer
from utils.tree import Interaction


def is_manager():
    async def predicate(interaction: Interaction) -> bool:
        assert interaction.guild is not None
        assert isinstance(interaction.user, discord.Member)

        category = interaction.namespace.category
        config = interaction.client.get_donation_config(interaction.guild, category)
        if not config:
            raise DonationCategoryError("That is not a valid donation category.")
        if interaction.user.guild_permissions.manage_guild:
            return True

        for role in config.managers:
            if role in interaction.user.roles:
                return True
        else:
            raise DonationPermissionsError(
                "You do not have permissions to use this command."
            )

    return app_commands.check(predicate)


class DonationsLeaderboardPaginator(BaseButtonPaginator[asyncpg.Record]):
    async def format_page(self, donations: List[asyncpg.Record], /) -> discord.Embed:
        assert self.bot is not None
        extras = self.extras or {}
        description = "The top donors of this server are:\n\n"

        for i, record in enumerate(donations):
            description += f"`{i + 1}.` <@!{record['member']}> - **{extras.get('symbol')} {record['amount']:,}**\n"

        embed = discord.Embed(
            title=f"{MONEY_EMOJI} Top {extras.get('category') } Donors",
            description=description,
            color=self.bot.colour,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar)

        embed.set_footer(text=f"Page {self.current_page}/{self.total_pages}")

        return embed


class DonationCommands(commands.GroupCog):
    """Main cog for updating user donations."""

    bot: Giftify

    async def update_roles(
        self, member: discord.Member, amount: int, config: GuildDonationConfig
    ) -> Tuple[List[str], List[str]]:
        to_add: List[discord.Role] = []
        to_remove: List[discord.Role] = []

        for role_amount, role in config.roles.items():
            if amount >= role_amount:
                if role not in member.roles:
                    to_add.append(role)
            else:
                if role in member.roles:
                    to_remove.append(role)

        try:
            await member.add_roles(*to_add)
        except discord.HTTPException:
            pass

        try:
            await member.remove_roles(*to_remove)
        except discord.HTTPException:
            pass

        return [role.mention for role in to_add], [role.mention for role in to_remove]

    async def update_donation(
        self,
        *,
        member: discord.Member,
        amount: int,
        action: DonationAction,
        config: GuildDonationConfig,
    ) -> Tuple[int, List[str], List[str]]:
        async with self.bot.pool.acquire() as connection:
            async with connection.transaction():
                query = """SELECT amount FROM donations
                        WHERE member = $1 AND guild = $2 AND category = $3"""
                existing_amount = await connection.fetchval(
                    query, member.id, member.guild.id, config.category
                )

                if action == DonationAction.ADD:
                    query = """INSERT INTO donations (member, guild, category, amount)
                            VALUES ($1, $2, $3, $4)
                            ON CONFLICT (member, guild, category)
                            DO UPDATE SET amount = donations.amount + $4
                            RETURNING amount"""
                    updated_amount = await connection.fetchval(
                        query, member.id, member.guild.id, config.category, amount
                    )
                else:
                    if existing_amount is None or amount > existing_amount:
                        raise DonationError(
                            "Cannot remove more than the existing amount."
                        )
                    else:
                        query = """UPDATE donations
                                SET amount = amount - $1
                                WHERE member = $2 AND guild = $3 AND category = $4
                                RETURNING amount"""
                        updated_amount = await connection.fetchval(
                            query, amount, member.id, member.guild.id, config.category
                        )

                roles_added, roles_removed = await self.update_roles(
                    member, updated_amount, config
                )

                return updated_amount, roles_added, roles_removed

    @app_commands.command(name="add")
    @app_commands.describe(
        category="The name of the donation category.",
        amount="The amount of donations to add.",
        member="The member whose donations will be tracked.",
    )
    @is_manager()
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def donation_add(
        self,
        interaction: Interaction,
        category: Transform[GuildDonationConfig, DonationCategoryTransformer],
        member: discord.Member,
        amount: Transform[int, AmountTransformer],
    ) -> None:
        """Add some amount to user's donations."""
        await interaction.response.defer()
        assert interaction.guild is not None

        updated_amount, roles_added, roles_removed = await self.update_donation(
            member=member,
            amount=amount,
            action=DonationAction.ADD,
            config=category,
        )

        embed = discord.Embed(
            title="Donation Added",
            description=f"{SUCCESS_EMOJI} The amount of **{category.symbol} {amount:,}** has been added to {member.mention}'s donations.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(),
        )

        embed.add_field(name=f"{DONATE_EMOJI} Category", value=category.category)
        embed.add_field(
            name=f"{MONEY_EMOJI} Updated Amount",
            value=f"**{category.symbol} {updated_amount:,}**",
        )
        if roles_added:
            embed.add_field(
                name=f"{PLUS_EMOJI} Roles Added",
                value=", ".join(roles_added),
                inline=False,
            )
        if roles_removed:
            embed.add_field(
                name=f"{MINUS_EMOJI} Roles Removed",
                value=", ".join(roles_removed),
                inline=False,
            )
        embed.set_thumbnail(url=member.display_avatar)

        embed.set_author(
            name=interaction.user.display_name, icon_url=interaction.user.display_avatar
        )

        await interaction.followup.send(embed=embed)

        self.bot.dispatch(
            "donation_action",
            DonationAction.ADD,
            amount,
            updated_amount,
            member,
            interaction.user,
            category,
        )

    @app_commands.command(name="remove")
    @app_commands.describe(
        category="The name of the donation category.",
        amount="The amount of donations to remove.",
        member="The member whose donations will be tracked.",
    )
    @is_manager()
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def donation_remove(
        self,
        interaction: Interaction,
        category: Transform[GuildDonationConfig, DonationCategoryTransformer],
        member: discord.Member,
        amount: Transform[int, AmountTransformer],
    ) -> None:
        """Remove some amount from user's donations."""
        await interaction.response.defer()
        assert interaction.guild is not None

        try:
            updated_amount, roles_added, roles_removed = await self.update_donation(
                member=member,
                amount=amount,
                action=DonationAction.REMOVE,
                config=category,
            )
        except DonationError as error:
            return await interaction.client.send(interaction, str(error), "error")

        embed = discord.Embed(
            title="Donation Removed",
            description=f"{SUCCESS_EMOJI} The amount of **{category.symbol} {amount:,}** has been removed from {member.mention}'s donations.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(),
        )

        embed.add_field(name=f"{DONATE_EMOJI} Category", value=category.category)
        embed.add_field(
            name=f"{MONEY_EMOJI} Updated Amount",
            value=f"**{category.symbol} {updated_amount:,}**",
        )
        if roles_added:
            embed.add_field(
                name=f"{PLUS_EMOJI} Roles Added",
                value=", ".join(roles_added),
                inline=False,
            )
        if roles_removed:
            embed.add_field(
                name=f"{MINUS_EMOJI} Roles Removed",
                value=", ".join(roles_removed),
                inline=False,
            )
        embed.set_thumbnail(url=member.display_avatar)

        embed.set_author(
            name=interaction.user.display_name, icon_url=interaction.user.display_avatar
        )

        await interaction.followup.send(embed=embed)

        self.bot.dispatch(
            "donation_action",
            DonationAction.REMOVE,
            amount,
            updated_amount,
            member,
            interaction.user,
            category,
        )

    @app_commands.command(name="sync")
    @app_commands.describe(
        category="The name of the donation category.",
        member="The member whose donations will be synced.",
    )
    @is_manager()
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def donation_sync(
        self,
        interaction: Interaction,
        category: Transform[GuildDonationConfig, DonationCategoryTransformer],
        member: discord.Member,
    ) -> None:
        """Sync donation roles of a user as per their donations."""
        await interaction.response.defer()
        assert interaction.guild is not None

        amount = (
            await self.bot.pool.fetchval(
                "SELECT amount FROM donations WHERE member = $1 AND guild = $2 AND category = $3 LIMIT 1",
                member.id,
                interaction.guild.id,
                category.category,
            )
            or 0
        )

        roles_added, roles_removed = await self.update_roles(member, amount, category)

        embed = discord.Embed(
            title="Donation Synced",
            description=f"{SUCCESS_EMOJI} The donation roles of user {member.mention} has been synced for amount **{category.symbol} {amount:,}**.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(),
        )

        embed.add_field(name=f"{DONATE_EMOJI} Category", value=category.category)
        if roles_added:
            embed.add_field(
                name=f"{PLUS_EMOJI} Roles Added",
                value=", ".join(roles_added),
                inline=False,
            )
        if roles_removed:
            embed.add_field(
                name=f"{MINUS_EMOJI} Roles Removed",
                value=", ".join(roles_removed),
                inline=False,
            )
        embed.set_thumbnail(url=member.display_avatar)

        embed.set_author(
            name=interaction.user.display_name, icon_url=interaction.user.display_avatar
        )

        await interaction.followup.send(embed=embed)

        self.bot.dispatch(
            "donation_action",
            DonationAction.SYNC,
            0,
            amount,
            member,
            interaction.user,
            category,
        )

    @app_commands.command(name="check")
    @app_commands.describe(
        category="The name of the donation category.",
        member="The member whose donation is to be checked.",
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def donation_check(
        self,
        interaction: Interaction,
        category: Transform[GuildDonationConfig, DonationCategoryTransformer],
        member: Optional[discord.Member] = None,
    ) -> None:
        """Check the donation of a user."""
        await interaction.response.defer()
        assert interaction.guild is not None
        if not member:
            assert isinstance(interaction.user, discord.Member)
            member = interaction.user

        amount = (
            await self.bot.pool.fetchval(
                "SELECT amount FROM donations WHERE member = $1 AND guild = $2 AND category = $3 LIMIT 1",
                member.id,
                interaction.guild.id,
                category.category,
            )
            or 0
        )

        embed = discord.Embed(
            title="Donation",
            description=f"{MONEY_EMOJI} {member.mention} has donated **{category.symbol} {amount:,}** for `{category.category}`.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(),
        )

        embed.set_thumbnail(url=member.display_avatar)
        embed.set_author(name=member.display_name, icon_url=member.display_avatar)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="leaderboard")
    @app_commands.describe(
        category="The name of the donation category.",
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def donation_leaderboard(
        self,
        interaction: Interaction,
        category: Transform[GuildDonationConfig, DonationCategoryTransformer],
    ) -> None:
        """Check the donation leaderboard of a category in the current guild."""
        await interaction.response.defer()
        assert interaction.guild is not None

        data = await self.bot.pool.fetch(
            "SELECT member, amount FROM donations WHERE guild = $1 AND category = $2 ORDER BY amount DESC",
            interaction.guild.id,
            category.category,
        )
        if data:
            paginator = DonationsLeaderboardPaginator(
                entries=data,
                per_page=10,
                target=interaction,
                extras={"symbol": category.symbol, "category": category.category},
            )
            embed = await paginator.embed()
            await interaction.followup.send(embed=embed, view=paginator)
        else:
            await interaction.client.send(
                interaction=interaction,
                message="There aren't any donors in this guild.",
                reason="warn",
            )

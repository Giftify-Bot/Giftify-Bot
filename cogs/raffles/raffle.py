from typing import List, Optional, Tuple, Union

import discord
from discord import app_commands
from discord.app_commands import Range, Transform
from discord.ext import commands

from core.bot import Giftify
from core.tree import Interaction
from models.raffles import Raffle
from utils.constants import GIVEAWAY_EMOJI, MONEY_EMOJI
from utils.paginator import BaseButtonPaginator
from utils.transformers import MentionablesTransformer, RaffleTransformer


class RafflesPaginator(BaseButtonPaginator[Raffle]):
    async def format_page(self, raffles: List[Raffle], /) -> discord.Embed:
        assert self.bot is not None
        extras = self.extras or {}
        description = "The raffles in this guild are:\n\n"

        embed = discord.Embed(
            title=f"{MONEY_EMOJI} {extras['guild'].name}'s Raffles",
            description=description,
            color=self.bot.colour,
        )
        for i, raffle in enumerate(raffles):
            embed.add_field(
                name=f"`{i + 1}.` {raffle.name}",
                value=(
                    f"Deputy Roles: {', '.join(role.mention for role in raffle.deputy_roles)}\n"
                    f"Deputy Members: {', '.join(member.mention for member in raffle.deputy_members)}\n"
                    f"Winner: {raffle.winner.mention if raffle.winner else None}\n"
                    f"Total Tickets: {sum(raffle.tickets.values())}\n"
                ),
                inline=False,
            )

        embed.set_thumbnail(url=self.bot.user.display_avatar)

        embed.set_footer(text=f"Page {self.current_page}/{self.total_pages}")

        return embed


class TicketsLeaderboardPaginator(BaseButtonPaginator[Tuple[discord.Member, int]]):
    async def format_page(
        self, tickets: List[Tuple[discord.Member, int]], /
    ) -> discord.Embed:
        assert self.bot is not None
        extras = self.extras or {}
        description = f"The tickets of {extras['name']} raffle are:\n\n"

        for i, member_tickets in enumerate(tickets):
            description += (
                f"`{i + 1}.` {member_tickets[0].mention} - **{member_tickets[1]:,}**\n"
            )

        embed = discord.Embed(
            title=f"{MONEY_EMOJI} {extras['name'].title()} Raffle",
            description=description,
            color=self.bot.colour,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar)

        embed.set_footer(text=f"Page {self.current_page}/{self.total_pages}")

        return embed


class RaffleBase(commands.GroupCog):
    """Cog containing admin commands for raffle management."""

    bot: Giftify

    @app_commands.command(name="create")
    @app_commands.describe(
        name="The unique name of the raffle.",
        deputies="The list of members or roles who can manage the raffle.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def raffle_create(
        self,
        interaction: Interaction,
        name: Range[str, 3, 50],
        deputies: Optional[
            Transform[
                List[Union[discord.Member, discord.Role]], MentionablesTransformer
            ]
        ] = None,
    ) -> None:
        """Creates a new raffle."""
        await interaction.response.defer()
        assert interaction.guild is not None

        raffles = await self.bot.fetch_raffles(guild=interaction.guild)

        if len(raffles) >= 25:
            return await interaction.client.send(
                interaction=interaction,
                message="You cannot create more than 25 raffles.",
                reason="error",
            )

        deputy_roles = (
            [
                mentionable
                for mentionable in deputies
                if isinstance(mentionable, discord.Role)
            ]
            if deputies
            else []
        )

        deputy_members = (
            [
                mentionable
                for mentionable in deputies
                if isinstance(mentionable, discord.Member)
            ]
            if deputies
            else []
        )

        if len(deputy_roles) >= 10:
            return await interaction.client.send(
                interaction=interaction,
                message="You cannot add more than 10 deputy roles.",
                reason="error",
            )

        if len(deputy_members) >= 25:
            return await interaction.client.send(
                interaction=interaction,
                message="You cannot add more than 25 deputy members.",
                reason="error",
            )

        raffle = Raffle(
            self.bot.pool,
            guild=interaction.guild,
            name=name,
            winner=None,
            deputy_roles=deputy_roles,
            deputy_members=deputy_members,
            tickets={},
        )

        if raffle in raffles:
            return await interaction.client.send(
                interaction=interaction,
                message=f"Raffle of name {raffle.name} already exists!",
                reason="error",
            )

        cache = self.bot.raffles_cache.get(interaction.guild, [])
        cache.append(raffle)
        self.bot.raffles_cache[interaction.guild] = cache

        await raffle.save()

        await interaction.client.send(
            interaction=interaction,
            message=f"Successfully created the raffle {raffle.name}.",
        )

    @app_commands.command(name="delete")
    @app_commands.describe(
        raffle="The unique name of the raffle.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def raffle_delete(
        self,
        interaction: Interaction,
        raffle: Transform[Raffle, RaffleTransformer],
    ) -> None:
        """Deletes a raffle."""
        await interaction.response.defer()
        assert interaction.guild is not None

        await raffle.delete()

        cache = self.bot.raffles_cache.get(interaction.guild, [])
        cache.remove(raffle)
        self.bot.raffles_cache[interaction.guild] = cache

        await interaction.client.send(
            interaction=interaction,
            message=f"Successfully deleted the raffle {raffle.name!r}.",
        )

    @app_commands.command(name="list")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def raffle_list(self, interaction: Interaction) -> None:
        """List all raffles in a guild."""
        await interaction.response.defer()
        assert interaction.guild is not None

        raffles = await self.bot.fetch_raffles(interaction.guild, use_cache=False)

        if raffles:
            paginator = RafflesPaginator(
                entries=raffles,
                per_page=5,
                target=interaction,
                extras={"guild": interaction.guild},
            )
            embed = await paginator.embed()
            return await interaction.followup.send(embed=embed, view=paginator)

        await interaction.client.send(
            interaction=interaction,
            message="There aren't any raffles in this server",
            reason="warn",
        )

    @app_commands.command(name="show")
    @app_commands.describe(
        raffle="The unique name of the raffle.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def raffle_show(
        self,
        interaction: Interaction,
        raffle: Transform[Raffle, RaffleTransformer],
    ) -> None:
        """Displays tickets of a raffle."""
        await interaction.response.defer()

        entries = list(
            sorted(
                raffle.tickets.items(),
                key=lambda t: t[1],
                reverse=True,
            )
        )

        if entries:
            paginator = TicketsLeaderboardPaginator(
                entries=entries,
                per_page=5,
                target=interaction,
                extras={"name": raffle.name},
            )
            embed = await paginator.embed()
            return await interaction.followup.send(embed=embed, view=paginator)

        await interaction.client.send(
            interaction=interaction,
            message="There are no tickets in that raffle",
            reason="warn",
        )

    @app_commands.command(name="roll")
    @app_commands.describe(
        raffle="The unique name of the raffle.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def raffle_roll(
        self,
        interaction: Interaction,
        raffle: Transform[Raffle, RaffleTransformer],
    ) -> None:
        """Displays tickets of a raffle."""
        await interaction.response.defer()

        if not raffle.tickets:
            return await interaction.client.send(
                interaction=interaction,
                message="Hey, there are no raffle participants yet. You cannot roll a winner",
                ephemeral=True,
            )

        winner = await raffle.roll()

        await interaction.followup.send(
            f"{GIVEAWAY_EMOJI} Congratulations {winner.mention}, you have won the raffle **`{raffle.name}`**!",
            allowed_mentions=discord.AllowedMentions(users=[winner]),
        )

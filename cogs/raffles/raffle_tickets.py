import discord
from discord import app_commands
from discord.app_commands import Transform
from discord.ext import commands

from core.bot import Giftify
from core.tree import Interaction
from models.raffles import Raffle
from utils.exceptions import RaffleError
from utils.transformers import RaffleTransformer


def is_deputy(member: discord.Member, raffle: Raffle) -> bool:
    if member.guild_permissions.manage_guild or member in raffle.deputy_members:
        return True

    return any([role for role in raffle.deputy_roles if role in member.roles])


class RaffleTickets(commands.GroupCog):
    """Cog containing admin commands for raffle management."""

    bot: Giftify

    tickets = app_commands.Group(
        name="tickets",
        description="Add or remove tickets to a member in a raffle.",
        guild_only=True,
    )

    @tickets.command(name="add")
    @app_commands.describe(
        raffle="The unique name of the raffle.",
        member="The participant to whom tickets will be added.",
        tickets="The number of tickets to be added.",
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def raffle_tickets_add(
        self,
        interaction: Interaction,
        raffle: Transform[Raffle, RaffleTransformer],
        member: discord.Member,
        tickets: app_commands.Range[int, 1, 1_000_000_000],
    ) -> None:
        """Adds tickets to a member."""
        await interaction.response.defer()
        assert isinstance(interaction.user, discord.Member)

        if not is_deputy(interaction.user, raffle):
            return await interaction.client.send(
                interaction=interaction,
                message="You do not have permissions to use this command.",
                reason="error",
            )

        await raffle.add_tickets(member, tickets)

        await interaction.client.send(
            interaction=interaction,
            message=f"Successfully added `{tickets}` tickets to {member.mention}.",
        )

    @tickets.command(name="remove")
    @app_commands.describe(
        raffle="The unique name of the raffle.",
        member="The participant from whom tickets will be removed.",
        tickets="The number of tickets to be removed.",
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def raffle_tickets_remove(
        self,
        interaction: Interaction,
        raffle: Transform[Raffle, RaffleTransformer],
        member: discord.Member,
        tickets: app_commands.Range[int, 1, 1_000_000_000],
    ) -> None:
        """Removes tickets from a member."""
        await interaction.response.defer()
        assert isinstance(interaction.user, discord.Member)

        if not is_deputy(interaction.user, raffle):
            return await interaction.client.send(
                interaction=interaction,
                message="You do not have permissions to use this command.",
                reason="error",
            )

        try:
            await raffle.remove_tickets(member, tickets)
        except RaffleError as error:
            return await interaction.client.send(
                interaction=interaction,
                message=str(error),
                reason="warn",
                ephemeral=True,
            )

        await interaction.client.send(
            interaction=interaction,
            message=f"Successfully removed `{tickets}` tickets from {member.mention}.",
        )

    @tickets.command(name="show")
    @app_commands.describe(
        raffle="The unique name of the raffle.",
        member="The participant whose tickets will be displayed.",
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def raffle_tickets_show(
        self,
        interaction: Interaction,
        raffle: Transform[Raffle, RaffleTransformer],
        member: discord.Member,
    ) -> None:
        """Shows tickets of a member."""
        await interaction.response.defer()
        assert interaction.guild is not None

        tickets = raffle.tickets.get(member)
        if tickets and tickets > 0:
            return await interaction.followup.send(
                f"{member.mention} has {tickets} tickets in raffle **`{raffle.name}`**.",
                ephemeral=True,
            )

        await interaction.followup.send(
            f"{member.mention} does not have any tickets in raffle **`{raffle.name}`**.",
            ephemeral=True,
        )

from typing import Union

import discord
from discord import app_commands
from discord.app_commands import Transform
from discord.ext import commands

from bot import Giftify
from models.raffles import Raffle
from utils.exceptions import RaffleError
from utils.transformers import RaffleTransformer
from utils.tree import Interaction


class RaffleDeputy(commands.GroupCog):
    """Cog containing admin commands for raffle management."""

    bot: Giftify

    deputy = app_commands.Group(
        name="deputy",
        description="Manage the raffle deputy roles or members.",
        guild_only=True,
    )

    @deputy.command(name="add")
    @app_commands.describe(
        raffle="The unique name of the raffle.",
        role_or_member="A role or member mention or ID.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def raffle_deputy_add(
        self,
        interaction: Interaction,
        raffle: Transform[Raffle, RaffleTransformer],
        role_or_member: Union[discord.Member, discord.Role],
    ) -> None:
        """Adds a raffle deputy."""
        await interaction.response.defer()

        try:
            await raffle.add_deputy(role_or_member)
        except RaffleError as error:
            return await interaction.client.send(
                interaction=interaction,
                message=str(error),
                reason="warn",
                ephemeral=True,
            )

        await interaction.client.send(
            interaction=interaction,
            message=f"Successfully added {role_or_member} as a deputy.",
        )

    @deputy.command(name="remove")
    @app_commands.describe(
        raffle="The unique name of the raffle.",
        role_or_member="A role or member mention or ID.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def raffle_deputy_remove(
        self,
        interaction: Interaction,
        raffle: Transform[Raffle, RaffleTransformer],
        role_or_member: Union[discord.Member, discord.Role],
    ) -> None:
        """Removes a raffle deputy."""
        await interaction.response.defer()

        try:
            await raffle.remove_deputy(role_or_member)
        except RaffleError as error:
            return await interaction.client.send(
                interaction=interaction,
                message=str(error),
                reason="warn",
                ephemeral=True,
            )

        await interaction.client.send(
            interaction=interaction,
            message=f"Successfully removed {role_or_member} as a deputy.",
        )

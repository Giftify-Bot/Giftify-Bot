from typing import List

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands

from core.bot import Giftify
from core.tree import Interaction
from utils.constants import GIFT_EMOJI
from utils.paginator import BaseButtonPaginator


class ManagersPaginator(BaseButtonPaginator[int]):
    async def format_page(self, managers: List[asyncpg.Record], /) -> discord.Embed:
        assert self.bot is not None

        description = "The top giveaway managers of this server are:\n\n"

        for i, record in enumerate(managers):
            description += f"`{i + 1}.` <@!{record['host']}> - **{record['count']}** giveaway(s) hosted!\n"

        embed = discord.Embed(
            title=f"{GIFT_EMOJI} Top Giveaway Managers",
            description=description,
            color=self.bot.colour,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar)

        embed.set_footer(text=f"Page {self.current_page}/{self.total_pages}")

        return embed


class GiveawayTop(commands.GroupCog):
    """Check the top giveaway managers of the guild"""

    bot: Giftify

    @app_commands.command(name="top")
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def giveaway_top(
        self,
        interaction: Interaction,
    ):
        """Check the top giveaway managers of the server."""
        assert interaction.guild is not None

        await interaction.response.defer()

        records = await self.bot.pool.fetch(
            "SELECT * FROM stats WHERE guild = $1 ORDER BY count DESC",
            interaction.guild.id,
        )
        if records:
            view = ManagersPaginator(entries=records, per_page=10, target=interaction)
            embed = await view.embed()
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.client.send(
                interaction, "No records found for this guild.", "warn"
            )

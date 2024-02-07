from typing import List

import discord
from discord import app_commands
from discord.ext import commands

from core.bot import Giftify
from core.tree import Interaction
from models.giveaways import Giveaway
from utils.constants import CROWN_EMOJI, GIFT_EMOJI, TIMER_EMOJI, TROPHY_EMOJI
from utils.paginator import BaseButtonPaginator


class GiveawaysPaginator(BaseButtonPaginator[Giveaway]):
    async def format_page(self, giveaways: List[Giveaway], /) -> discord.Embed:
        assert self.bot is not None

        embed = discord.Embed(title="Giveaway", colour=self.bot.colour)

        giveaway = giveaways[0]
        host = await self.bot.get_or_fetch_user(giveaway.host_id)

        embed.add_field(
            name=f"{GIFT_EMOJI} Prize",
            value=giveaway.prize,
            inline=False,
        )
        embed.add_field(
            name=f"{TIMER_EMOJI} Ends",
            value=discord.utils.format_dt(giveaway.ends, style="R"),
            inline=False,
        )
        if host:
            embed.set_author(name=host.display_name, icon_url=host.display_avatar)
            embed.add_field(
                name=f"{CROWN_EMOJI} Host", value=host.mention, inline=False
            )
        embed.add_field(
            name=f"{TROPHY_EMOJI} Winner Count",
            value=giveaway.winner_count,
            inline=False,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar)

        embed.set_footer(text=f"Page {self.current_page}/{self.total_pages}")

        return embed


class GiveawayList(commands.GroupCog):
    """Check the list of giveaways."""

    bot: Giftify

    @app_commands.command(name="list")
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def giveaway_list(
        self,
        interaction: Interaction,
    ):
        """Check the list of ongoing giveaways."""
        assert interaction.guild is not None

        await interaction.response.defer()

        giveaways = await self.bot.running_giveaways(
            guild_id=interaction.guild.id, sort_by_ends=True
        )

        if giveaways:
            view = GiveawaysPaginator(entries=giveaways, per_page=1, target=interaction)
            embed = await view.embed()
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.client.send(
                interaction,
                "There aren't any giveaways running in this server.",
                "warn",
            )

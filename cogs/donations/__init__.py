import datetime
from typing import List, Optional, Union

import discord
from discord import app_commands
from discord.ext import commands

from core.bot import Giftify
from models.donation_settings import DonationAction, GuildDonationConfig
from utils.constants import (
    CROWN_EMOJI,
    DONATE_EMOJI,
    MONEY_EMOJI,
    PARTICIPANTS_EMOJI,
    TROPHY_EMOJI,
)

# Command imports
from .donation_autoroles import DonationAutorole
from .donation_category import DonationCategory
from .donation_settings import DonationSettings
from .donations import DonationCommands


@app_commands.guild_only()
class Donations(
    DonationAutorole,
    DonationCategory,
    DonationCommands,
    DonationSettings,
    name="donation",
):
    """Cog for tracking donations."""

    def __init__(self, bot: Giftify) -> None:
        self.bot = bot

        self.bot.loop.create_task(self.load_configs())

        super().__init__()

    async def load_configs(self):
        if not self.bot.is_ready():
            await self.bot.wait_until_ready()

        records = await self.bot.pool.fetch("SELECT * FROM donation_configs")
        configs: List[GuildDonationConfig] = []
        for record in records:
            config = await GuildDonationConfig.from_record(self.bot, record=record)
            if config:
                configs.append(config)

        self.bot.donation_configs = configs

    @commands.Cog.listener()
    async def on_donation_action(
        self,
        action: DonationAction,
        amount: int,
        updated_amount: int,
        member: discord.Member,
        manager: Union[discord.Member, discord.User],
        config: GuildDonationConfig,
    ) -> None:
        if not config.logging:
            return

        description = (
            f"{DONATE_EMOJI} **Amount:** **{config.symbol} {amount:,}**\n"
            f"{MONEY_EMOJI} **Updated Amount:** **{config.symbol} {updated_amount:,}**\n"
            f"{PARTICIPANTS_EMOJI} **Member:** {member.mention}\n"
            f"{CROWN_EMOJI} **Manager:** {manager.mention}\n"
            f"{TROPHY_EMOJI} **Category:** {config.category}\n"
        )

        embed = discord.Embed(
            title=f"Donation {str(action)}",
            description=description,
            colour=self.bot.colour,
            timestamp=datetime.datetime.now(),
        )
        embed.set_author(name=manager.display_name, icon_url=manager.display_avatar)
        embed.set_thumbnail(url=member.display_avatar)

        await self.bot.send_to_webhook(channel=config.logging, embed=embed)


async def setup(bot: Giftify) -> None:
    await bot.add_cog(Donations(bot))

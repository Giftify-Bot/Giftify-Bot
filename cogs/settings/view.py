import datetime

import discord
from discord import app_commands
from discord.ext import commands

from utils.constants import (
    ARROW_EMOJI,
    BLANK_SPACE,
    OFF_EMOJI,
    ON_EMOJI,
    SETTINGS_EMOJI,
)
from utils.tree import Interaction


def emoji(value: bool) -> str:
    return ON_EMOJI if value else OFF_EMOJI


def enabled(value: bool) -> str:
    return "**Enabled**" if value else "**Disabled**"


class GiveawayView(commands.GroupCog):
    """View the giveaway settings for this server."""

    @app_commands.command(name="view")
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def view(self, interaction: Interaction):
        """View the giveaway settings for this server."""

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)

        embed = discord.Embed(
            title=f"{SETTINGS_EMOJI} Giveaway Settings for {interaction.guild.name}",
            colour=config.color,
            timestamp=datetime.datetime.now(),
        )
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon)

        embed.add_field(
            name="Logging",
            value=f"{BLANK_SPACE}{ARROW_EMOJI} {config.logging.mention if config.logging else '**Not Set**'}",
            inline=False,
        )
        embed.add_field(
            name="Ping Role",
            value=f"{BLANK_SPACE}{ARROW_EMOJI} {config.ping.mention if config.ping else '**Not Set**'}",
            inline=False,
        )
        embed.add_field(
            name="Reaction Emoji",
            value=f"{BLANK_SPACE}{ARROW_EMOJI} {config.reaction}",
            inline=False,
        )
        embed.add_field(
            name="Default Roles",
            value=(
                f"{BLANK_SPACE}{ARROW_EMOJI} **Required Roles:** {','.join(role.mention for role in config.required_roles if role is not None) if config.required_roles else 'None'}\n"
                f"{BLANK_SPACE}{ARROW_EMOJI} **Blacklisted Roles:** {','.join(role.mention for role in config.blacklisted_roles if role is not None) if config.blacklisted_roles else 'None'}\n"
                f"{BLANK_SPACE}{ARROW_EMOJI} **Bypass Roles:** {','.join(role.mention for role in config.bypass_roles if role is not None) if config.bypass_roles else 'None'}\n"
                f"{BLANK_SPACE}{ARROW_EMOJI} **Bonus Roles:** {','.join(f'{role.mention}: {multiplier_roles}' for role, multiplier_roles in config.multiplier_roles.items() if role is not None) if config.multiplier_roles else 'None'}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Manager Roles",
            value=(
                f"{BLANK_SPACE}{ARROW_EMOJI} {','.join(role.mention for role in config.managers if role is not None) if config.managers else 'None'}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Button Color",
            value=(
                f"{BLANK_SPACE}{ARROW_EMOJI} **{config.button_style.name.capitalize()}**"
            ),
            inline=False,
        )
        embed.add_field(
            name="DM Host",
            value=(
                f"{BLANK_SPACE}{ARROW_EMOJI} {emoji(config.dm_host)} {enabled(config.dm_host)}"
            ),
            inline=False,
        )
        embed.add_field(
            name="DM Winner",
            value=(
                f"{BLANK_SPACE}{ARROW_EMOJI} {emoji(config.dm_winner)} {enabled(config.dm_host)}"
            ),
            inline=False,
        )
        embed.add_field(
            name="End Message",
            value=(f"{BLANK_SPACE}{ARROW_EMOJI} {config.end_message}"),
            inline=False,
        )
        embed.add_field(
            name="Reroll Message",
            value=(f"{BLANK_SPACE}{ARROW_EMOJI} {config.reroll_message}"),
            inline=False,
        )
        embed.add_field(
            name="DM Host Message",
            value=(f"{BLANK_SPACE}{ARROW_EMOJI} {config.dm_host_message}"),
            inline=False,
        )
        embed.add_field(
            name="DM Winner Message",
            value=(f"{BLANK_SPACE}{ARROW_EMOJI} {config.dm_message}"),
            inline=False,
        )
        embed.add_field(
            name="Giveaway Header",
            value=(f"{BLANK_SPACE}{ARROW_EMOJI} {config.gw_header}"),
            inline=False,
        )
        embed.add_field(
            name="Giveaway End Header",
            value=(f"{BLANK_SPACE}{ARROW_EMOJI} {config.gw_end_header}"),
            inline=False,
        )

        await interaction.followup.send(embed=embed)

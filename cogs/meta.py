import datetime
import sys
import time
from typing import List

import cpuinfo
import discord
import psutil
from colorama import Fore, Style
from discord import app_commands
from discord.ext import commands

from core.bot import Giftify
from core.tree import Interaction
from utils.constants import (
    ARROW_EMOJI,
    BLANK_SPACE,
    BOT_INVITE,
    DEVELOPER_EMOJI,
    GIFT_EMOJI,
    NETWORK_EMOJI,
    ONLINE_EMOJI,
    SETTINGS_EMOJI,
    SIGNAL_EMOJI,
    SOURCE_CODE,
    SUPPORT_SERVER,
    TOOLS_EMOJI,
    VOTE_URL,
)
from utils.view import MainView


class Meta(commands.Cog):
    """Get some information about the bot."""

    def __init__(self, bot: Giftify) -> None:
        self.bot = bot

    async def owners(self) -> List[str]:
        """Fetches the names of the bot owners using their user IDs."""
        owner_names = []
        if self.bot.owner_ids:
            for owner_id in self.bot.owner_ids:
                if owner := await self.bot.get_or_fetch_user(owner_id):
                    owner_names.append(f"{ARROW_EMOJI} **[{owner.display_name}](https://discord.com/users/{owner.id})**")
        return owner_names

    @app_commands.command()
    @app_commands.checks.cooldown(1, 3, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.guild_only()
    async def help(self, interaction: Interaction) -> None:
        """Retrieve information and assistance for Giftify."""

        await interaction.response.defer()

        embed = discord.Embed(
            title="Giftify Help",
            description="Welcome to Giftify Help Panel! Here you can find information and assistance to get started.",
            color=self.bot.colour,
        )
        embed.add_field(
            name=f"{GIFT_EMOJI} General Help",
            value=(
                f"{BLANK_SPACE}{ARROW_EMOJI} If you need help setting up Giftify or want to learn about its functionalities, visit the [Official Documentation](https://giftifybot.vercel.app/documentation).\n"
                f"{BLANK_SPACE}{ARROW_EMOJI} For quick troubleshooting, refer to the [FAQ](https://giftifybot.vercel.app/faq)."
            ),
            inline=False,
        )
        embed.add_field(
            name=f"{TOOLS_EMOJI} Support Assistance",
            value=f"{BLANK_SPACE}If you require personal assistance or have questions about Giftify, please visit our [Support Server](https://giftifybot.vercel.app/support).",
            inline=False,
        )

        embed.set_thumbnail(url=self.bot.user.display_avatar)

        view = MainView()

        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command()
    @app_commands.checks.cooldown(1, 3, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.guild_only()
    async def ping(self, interaction: Interaction) -> None:
        """Check the latency of the bot."""
        start_time = time.monotonic()

        await interaction.response.defer()
        end_time = time.monotonic()
        client_latency = round((end_time - start_time) * 1000)
        api_latency = round(self.bot.latency * 1000)

        database_start_time = time.monotonic()
        await self.bot.pool.fetchval("SELECT 1")
        database_end_time = time.monotonic()
        database_latency = round((database_end_time - database_start_time) * 1000)

        embed = discord.Embed(title="Ping Information", timestamp=datetime.datetime.now())

        if client_latency < 200 and api_latency < 100 and database_latency < 100:
            embed.color = discord.Color.green()
        elif client_latency < 500 and api_latency < 200 and database_latency < 200:
            embed.color = discord.Color.orange()
        else:
            embed.color = discord.Color.red()

        embed.add_field(
            name=f"{NETWORK_EMOJI} Client Latency",
            value=f"```ini\n[ {client_latency }ms ]\n```",
            inline=False,
        )
        embed.add_field(
            name=f"{SIGNAL_EMOJI} API Latency",
            value=f"```ini\n[ {api_latency }ms ]\n```",
            inline=False,
        )
        embed.add_field(
            name=f"{ONLINE_EMOJI} Database Latency",
            value=f"```ini\n[ {database_latency }ms ]\n```",
            inline=False,
        )
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar,
        )

        await interaction.followup.send(embed=embed)

    @app_commands.command()
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.guild_only()
    async def stats(self, interaction: Interaction) -> None:
        """Displays statistics and information about Giftify."""

        assert interaction.guild is not None

        await interaction.response.defer()

        cpu_cores = psutil.cpu_count()
        total_ram = psutil.virtual_memory().total / (1024**3)  # Convert to GB
        ram_used = psutil.virtual_memory().used / (1024**2)  # Convert to MB

        owner_names = await self.owners()

        embed = discord.Embed(title="Giftify - Statistics", color=discord.Color.green())
        embed.add_field(name=f"{DEVELOPER_EMOJI} Owners", value="\n".join(owner_names), inline=False)

        system = (
            "```ansi\n"
            f"{Fore.GREEN}{Style.BRIGHT}Processor - {cpuinfo.get_cpu_info()['brand_raw']}\n"
            f"CPU Cores - {cpu_cores}\n"
            f"Total RAM - {total_ram:.2f} GB\n"
            f"RAM Used - {ram_used:.2f} MB{Style.RESET_ALL}\n"
            "```"
        )
        embed.add_field(
            name=f"{SETTINGS_EMOJI} System",
            value=system,
            inline=False,
        )
        version = sys.version.split("\n")[0]
        library = (
            "```ansi\n"
            f"{Fore.BLUE}{Style.BRIGHT}OS - {sys.platform}\n"
            f"Python - {version}\n"
            f"Library - discord.py\n"
            f"Library Version - {discord.__version__}\n"
            f"Bot Version - {self.bot.__version_info__}{Style.RESET_ALL}\n"
            "```"
        )
        embed.add_field(
            name=f"{TOOLS_EMOJI} Library",
            value=library,
            inline=False,
        )

        embed.set_footer(
            text="Giftify Bot | Powered by Discord.py",
            icon_url=self.bot.user.display_avatar,
        )
        running_giveaways = await self.bot.running_giveaways()
        stats = (
            "```ansi\n"
            f"{Fore.RED}{Style.BRIGHT}Running Giveaways: {len(running_giveaways)}\n"
            f"Shard ID - {interaction.guild.shard_id}\n"
            f"Guild Count - {len(self.bot.guilds):,}\n"
            f"User Count - {sum([guild.member_count for guild in self.bot.guilds if guild.member_count]):,}\n"
            f"Latency - {round(self.bot.latency * 1000)} ms{Style.RESET_ALL}\n"
            "```"
        )
        embed.add_field(
            name=f"{NETWORK_EMOJI} Stats",
            value=stats,
            inline=False,
        )

        embed.set_thumbnail(url=self.bot.user.display_avatar)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar)
        await interaction.followup.send(embed=embed)

    @app_commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def invite(self, interaction: Interaction) -> None:
        """Invite the Bot to your server."""
        embed = discord.Embed(
            title="Invite the Bot 🤖",
            description="> Click the button below to invite the bot to your server!",
            color=discord.Colour.green(),
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Invite", url=BOT_INVITE))
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar,
        )
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def source(self, interaction: Interaction) -> None:
        """View the source code of the bot."""
        embed = discord.Embed(
            title="Source 🤖",
            description="> Click the button below to view the source code of bot!",
            color=discord.Colour.green(),
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Source", url=SOURCE_CODE))
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar,
        )
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def support(self, interaction: Interaction) -> None:
        """Join the support server."""
        embed = discord.Embed(
            title="Support Server 🛠️",
            description="> Join our support server for assistance and updates!",
            color=discord.Colour.green(),
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Join", url=SUPPORT_SERVER))
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar,
        )
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def vote(self, interaction: Interaction) -> None:
        """Vote for the Bot on top.gg."""
        embed = discord.Embed(
            title="Vote for the Bot 🗳️",
            description="> Help us grow by voting for the bot on top.gg!",
            color=discord.Colour.green(),
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Vote", url=VOTE_URL))
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar,
        )
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: Giftify) -> None:
    await bot.add_cog(Meta(bot))

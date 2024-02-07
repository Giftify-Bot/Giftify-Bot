from __future__ import annotations

import logging
import logging.handlers
from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from discord import Guild
    from discord.app_commands import Command

    from core.bot import Giftify
    from core.tree import Interaction


def setup_logger(name, filename, dt_fmt, fmt, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(level)

    handler = logging.handlers.RotatingFileHandler(
        filename=filename,
        encoding="utf-8",
        mode="w",
        maxBytes=32 * 1024 * 1024,
        backupCount=0,
    )

    handler.setFormatter(logging.Formatter(fmt, dt_fmt, style="{"))
    logger.addHandler(handler)
    return logger


# Setup command logger
command_dt_fmt = "%Y-%m-%d %H:%M:%S %Z%z"
command_fmt = "[{asctime}] | [{levelname:<7}] {name}: | {message}"
command_logger = setup_logger(
    "commands", "logs/commands.log", command_dt_fmt, command_fmt
)

# Setup guilds logger
guilds_dt_fmt = "%Y-%m-%d %H:%M:%S %Z%z"
guilds_fmt = "[{asctime}] | [{levelname:<7}] {name}: | {message}"
guilds_logger = setup_logger("guilds", "logs/guilds.log", guilds_dt_fmt, guilds_fmt)


class Logger(commands.Cog):
    def __init__(self, bot: Giftify):
        self.bot = bot

    @staticmethod
    def format_command(command: Command) -> str:
        fmt = "/"
        if parent := command.parent:
            if root_parent := parent.parent:
                fmt += root_parent.name + " "
            fmt += parent.name + " "
        fmt += command.name
        return fmt

    @commands.Cog.listener()
    async def on_app_command_completion(
        self, interaction: Interaction, command: Command
    ) -> None:
        assert interaction.guild is not None

        command_logger.info(
            f"Command {self.format_command(command)} used by {interaction.user.display_name} ({interaction.user.id}) in {interaction.guild.name} ({interaction.guild.id})."
        )

    @commands.Cog.listener()
    async def on_guild_join(self, guild: Guild):
        guilds_logger.info(
            f"Joined guild {guild.name} ({guild.id}) owned by {guild.owner_id}."
        )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: Guild):
        guilds_logger.info(
            f"Left guild {guild.name} ({guild.id}) owned by {guild.owner_id}."
        )


async def setup(bot: Giftify) -> None:
    await bot.add_cog(Logger(bot))

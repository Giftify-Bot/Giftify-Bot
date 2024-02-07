from typing import TYPE_CHECKING

import discord
import sentry_sdk
from discord import app_commands

try:
    from typing import TypeAlias
except ImportError:
    from typing_extensions import TypeAlias

from utils.constants import WARN_EMOJI
from utils.exceptions import (
    DonationCategoryError,
    DonationError,
    DonationPermissionsError,
    MaxChannelConfigCreationError,
    TransformerError,
)

if TYPE_CHECKING:
    from core.bot import Giftify

Interaction: TypeAlias = discord.Interaction["Giftify"]


class CommandTree(app_commands.CommandTree):
    client: "Giftify"

    async def on_error(
        self,
        interaction: Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        view = discord.ui.View()

        button = discord.ui.Button(label="Support", url="https://discord.gg/GQSGChbEKz")

        view.add_item(button)

        if not interaction.response.is_done():
            await interaction.response.defer(thinking=True, ephemeral=True)

        embed = discord.Embed(
            title="An error was raised while executing this command!",
            color=discord.Colour.red(),
        )

        if isinstance(error, app_commands.CommandInvokeError):
            if isinstance(error, MaxChannelConfigCreationError):
                embed.description = f"{WARN_EMOJI} You cannot setup configuration for more than 25 channels, please try removing some."
            elif isinstance(error, discord.HTTPException):
                embed.description = f"{WARN_EMOJI} Unknown HTTP error occured!"
            else:
                embed.description = f"{WARN_EMOJI} An unknown error occurred , my developers have been notified about this error."
                self.client.log_handler.log.exception(
                    "Exception occurred in the CommandTree:\n", exc_info=error
                )
                sentry_sdk.capture_exception(error)
        elif isinstance(error, app_commands.TransformerError):
            if isinstance(error, TransformerError):
                embed.description = f"{WARN_EMOJI} {error.message}"
            else:
                embed.description = f"{WARN_EMOJI} {str(error)}"

        elif isinstance(error, app_commands.MissingPermissions):
            missing = [
                perm.replace("_", " ").replace("guild", "server").title()
                for perm in error.missing_permissions
            ]

            format = "\n> ".join(missing)

            embed.description = f"{WARN_EMOJI} You are missing follwing permission(s) to run this command: \n\n> {format}"

        elif isinstance(error, app_commands.BotMissingPermissions):
            missing = [
                perm.replace("_", " ").replace("guild", "server").title()
                for perm in error.missing_permissions
            ]

            format = "\n> ".join(missing)

            embed.description = f"{WARN_EMOJI} I am missing follwing permission(s) to run this command: \n\n > {format}"

        elif isinstance(error, app_commands.CommandOnCooldown):
            cooldown = int(error.cooldown.per)
            retry_after = int(error.retry_after)
            embed.description = f"{WARN_EMOJI} The cooldown for this command is **{cooldown}s**. Try running the command again after **{retry_after}s**."

        elif isinstance(error, app_commands.CommandNotFound):
            embed.description = (
                f'{WARN_EMOJI} The command "{error.name}" was not found.'
            )
        elif isinstance(error, DonationError):
            embed.description = f"{WARN_EMOJI} {str(error)}"
        elif isinstance(error, app_commands.CheckFailure):
            if isinstance(error, (DonationCategoryError, DonationPermissionsError)):
                embed.description = f"{WARN_EMOJI} {str(error.message)}"
            else:
                return
        else:
            embed.description = f"{WARN_EMOJI} An unknown error occured, my developers have been notified about this errors."
            await interaction.followup.send(embed=embed, ephemeral=True)
            sentry_sdk.capture_exception(error)
            return self.client.log_handler.log.exception(
                "Exception occurred in the CommandTree:\n", exc_info=error
            )

        return await interaction.followup.send(embed=embed, ephemeral=True)

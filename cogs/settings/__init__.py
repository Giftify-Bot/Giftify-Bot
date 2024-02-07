import discord
from discord import app_commands

from core.bot import Giftify
from core.tree import Interaction

# Command imports
from .button_colour import GiveawayButtonColour
from .channel_settings import GiveawayChannelSettings
from .colour import GiveawayEmbedColour
from .defaults import GiveawayDefaults
from .dm_host import GiveawayDMHost
from .dm_host_message import GiveawayDMHostMessage
from .dm_message import GiveawayDMMessage
from .dm_winner import GiveawayDMWinner
from .end_message import GiveawayEndMessage
from .gw_end_header import GiveawayEndHeader
from .gw_header import GiveawayHeader
from .logging import GiveawayLogging
from .managers import GiveawayManagers
from .participants_reaction import GiveawayParticipantsReaction
from .ping import GiveawayPing
from .reaction import GiveawayReaction
from .reroll_message import GiveawayRerollMessage
from .view import GiveawayView


@app_commands.guild_only()
class GiveawaySettings(
    GiveawayButtonColour,
    GiveawayChannelSettings,
    GiveawayEmbedColour,
    GiveawayDefaults,
    GiveawayDMHost,
    GiveawayDMHostMessage,
    GiveawayDMMessage,
    GiveawayDMWinner,
    GiveawayEndMessage,
    GiveawayRerollMessage,
    GiveawayEndHeader,
    GiveawayHeader,
    GiveawayLogging,
    GiveawayParticipantsReaction,
    GiveawayManagers,
    GiveawayPing,
    GiveawayReaction,
    GiveawayView,
    name="settings",
):
    """Advanced giveaway management commands."""

    def __init__(self, bot: Giftify) -> None:
        self.bot = bot
        super().__init__()

    async def interaction_check(self, interaction: Interaction) -> bool:
        assert isinstance(interaction.user, discord.Member)
        if interaction.user.guild_permissions.manage_guild:
            return True
        else:
            await interaction.client.send(
                interaction,
                "You do not have permissions to use this command.",
                reason="error",
                ephemeral=True,
            )
            return False


async def setup(bot: Giftify) -> None:
    await bot.add_cog(GiveawaySettings(bot))

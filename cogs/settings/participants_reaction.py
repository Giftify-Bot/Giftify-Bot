import discord
from discord import app_commands
from discord.app_commands import Transform
from discord.ext import commands

from utils.transformers import EmojiTransformer
from utils.tree import Interaction


class GiveawayParticipantsReaction(commands.GroupCog):
    """Set the reaction emoji for participants button."""

    @app_commands.command(name="participants_reaction")
    @app_commands.describe(emoji="The emoji to use for participants button.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def participants_reaction(
        self, interaction: Interaction, emoji: Transform[str, EmojiTransformer()]
    ):
        """Set the reaction emoji for participants button."""

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)

        await config.update("participants_reaction", emoji, interaction.client.pool)

        message = f"Successfully set participants reaction emoji to {emoji!r}"

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

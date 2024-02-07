import discord
from discord import app_commands
from discord.app_commands import Transform
from discord.ext import commands

from core.tree import Interaction
from utils.transformers import EmojiTransformer


class GiveawayReaction(commands.GroupCog):
    """Set the reaction emoji for giveaways."""

    @app_commands.command(name="reaction")
    @app_commands.describe(emoji="The emoji to use for giveaways.")
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def reaction(
        self, interaction: Interaction, emoji: Transform[str, EmojiTransformer()]
    ):
        """Set the reaction emoji for giveaways."""

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        await interaction.response.defer(thinking=True)
        config = await interaction.client.fetch_config(interaction.guild)

        await config.update("reaction", emoji, interaction.client.pool)

        message = f"Successfully set giveaway reaction emoji to {emoji!r}"

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

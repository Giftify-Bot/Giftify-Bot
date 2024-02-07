import datetime
from collections import ChainMap
from typing import Dict, List, Optional

import discord
from discord import app_commands
from discord.app_commands import Transform
from discord.ext import commands

from core.bot import Giftify
from core.tree import Interaction
from models.giveaway_settings import ChannelConfig
from models.giveaways import Giveaway, GiveawayAction
from utils.transformers import (
    BonusRolesTransformer,
    RolesTransformer,
    TextChannelsTransformer,
    TimeTransformer,
)


class GiveawayStart(commands.GroupCog):
    """A cog for starting giveaways."""

    bot: Giftify

    @app_commands.command(name="start")
    @app_commands.describe(
        prize="The prize of the giveaway.",
        duration="The duration of the giveaway.",
        winners="The number of winners for the giveaway.",
        required_roles="The roles required to participate in the giveaway.",
        blacklisted_roles="The roles not allowed to participate in the giveaway.",
        bypass_roles="The roles that can bypass participation restrictions",
        multiplier_roles="Use the format <role:number_of_multiplier_roles_entries> split using a ':' (colon).",
        messages_required="The number of messages required to join the giveaway.",
        allowed_message_channels="The channels where users are allowed to send messages.",
        amari="The amari level required for the giveaway.",
        weekly_amari="The weekly amari xp required for the giveaway.",
        no_defaults="Flag to exclude default settings for the giveaway.",
        image="The attached image for the giveaway.",
        ping="Wheter to ping the server pingrole when the giveaway starts.",
        donor="The donating member for the giveaway.",
        message="The message to accompany the giveaway.",
    )
    @app_commands.checks.bot_has_permissions(
        embed_links=True, send_messages=True, view_channel=True, add_reactions=True
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def giveaway_start(
        self,
        interaction: Interaction,
        duration: Transform[datetime.datetime, TimeTransformer],
        winners: app_commands.Range[int, 1, 32],
        prize: app_commands.Range[str, 1, 255],
        required_roles: Optional[
            Transform[List[discord.Role], RolesTransformer]
        ] = None,
        blacklisted_roles: Optional[
            Transform[List[discord.Role], RolesTransformer]
        ] = None,
        bypass_roles: Optional[Transform[List[discord.Role], RolesTransformer]] = None,
        multiplier_roles: Optional[
            Transform[Dict[discord.Role, int], BonusRolesTransformer]
        ] = None,
        messages_required: Optional[app_commands.Range[int, 1, 1000]] = None,
        allowed_message_channels: Optional[
            Transform[List[discord.TextChannel], TextChannelsTransformer]
        ] = None,
        amari: Optional[app_commands.Range[int, 1, 1000]] = None,
        weekly_amari: Optional[app_commands.Range[int, 1, 1000]] = None,
        no_defaults: bool = False,
        image: Optional[discord.Attachment] = None,
        ping: bool = False,
        donor: Optional[discord.Member] = None,
        message: Optional[app_commands.Range[str, 1, 2000]] = None,
    ):
        """Initiate a giveaway within your server, allowing for optional entry requirements."""
        assert interaction.guild is not None
        assert isinstance(interaction.user, discord.Member)

        await interaction.response.defer(ephemeral=True)

        if not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.client.send(
                interaction,
                "You cannot use that command in this channel type.",
                reason="warn",
            )
        config = await interaction.client.fetch_config(interaction.guild)

        channel_config: Optional[ChannelConfig] = await config.get_channel_config(
            interaction.channel, create_if_not_exists=False
        )
        category_config: Optional[ChannelConfig] = (
            await config.get_channel_config(
                channel=interaction.channel.category, create_if_not_exists=False
            )
            if interaction.channel.category is not None
            else None
        )

        if not no_defaults:
            required_roles = list(
                {
                    role
                    for config_obj in [
                        required_roles,
                        config.required_roles,
                        channel_config.required_roles if channel_config else [],
                        category_config.required_roles if category_config else [],
                    ]
                    for role in config_obj or []
                }
            )

            bypass_roles = list(
                {
                    role
                    for config_obj in [
                        bypass_roles,
                        config.bypass_roles,
                        channel_config.bypass_roles if channel_config else [],
                        category_config.bypass_roles if category_config else [],
                    ]
                    for role in config_obj or []
                }
            )

            blacklisted_roles = list(
                {
                    role
                    for config_obj in [
                        blacklisted_roles,
                        config.blacklisted_roles,
                        channel_config.blacklisted_roles if channel_config else [],
                        category_config.blacklisted_roles if category_config else [],
                    ]
                    for role in config_obj or []
                }
            )

            multiplier_roles = dict(
                ChainMap(
                    multiplier_roles or {},
                    config.multiplier_roles,
                    channel_config.multiplier_roles if channel_config else {},
                    category_config.multiplier_roles if category_config else {},
                )
            )
        try:
            giveaway = await Giveaway.start(
                interaction=interaction,
                duration=duration,
                winners=winners,
                prize=prize,
                config=config,
                channel_config=channel_config,
                required_roles=required_roles,
                blacklisted_roles=blacklisted_roles,
                bypass_roles=bypass_roles,
                multiplier_roles=multiplier_roles,
                messages_required=messages_required,
                allowed_message_channels=allowed_message_channels,
                amari=amari,
                weekly_amari=weekly_amari,
                image=image,
                donor=donor,
                ping=ping,
                message=message,
            )
        except discord.HTTPException as error:
            if "Invalid emoji" in str(error):
                return await interaction.client.send(
                    interaction,
                    "Failed to start giveaway, update the reaction emoji to a valid emoji!",
                    reason="error",
                )
            else:
                raise

        if giveaway.messages_required and giveaway.messages_required > 0:
            self.bot.cached_giveaways.append(giveaway)

        self.bot.dispatch(
            "giveaway_action", GiveawayAction.START, giveaway, interaction.user
        )

        await interaction.client.send(interaction, "Successfully started the giveaway!")

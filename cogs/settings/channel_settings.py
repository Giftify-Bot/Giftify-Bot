import datetime
from typing import Optional, Union

import discord
from discord import app_commands
from discord.ext import commands

from utils.constants import ARROW_EMOJI, BLANK_SPACE, SETTINGS_EMOJI
from utils.tree import Interaction


class GiveawayChannelSettings(commands.GroupCog):
    """Edit channel giveaway settings."""

    channel = app_commands.Group(
        name="channel",
        description="Edit channel giveaway settings.",
        guild_only=True,
    )

    @channel.command(name="add_requirement")
    @app_commands.describe(
        role="Mention a role or enter a role ID.",
        channel="Mention the text channel or enter channel ID.",
    )
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def channel_add_requirement(
        self,
        interaction: Interaction,
        role: discord.Role,
        channel: Optional[Union[discord.TextChannel, discord.CategoryChannel]] = None,
    ):
        """Add a default requirement role for some channel."""

        await interaction.response.defer(thinking=True)
        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        if role.id == interaction.guild.id:
            await interaction.client.send(
                interaction,
                "You cannot add `@everyone` role as giveaway requirement role.",
                reason="warn",
            )

        if channel is None:
            if not isinstance(interaction.channel, discord.TextChannel):
                return await interaction.client.send(
                    interaction,
                    "You cannot use that command in this channel type.",
                    reason="warn",
                    ephemeral=True,
                )
            channel = interaction.channel

        guild_config = await interaction.client.fetch_config(interaction.guild)
        channel_config = await guild_config.get_channel_config(
            channel=channel,
            create_if_not_exists=True,
            pool=interaction.client.pool,
        )
        required_roles = channel_config.required_roles
        if len(required_roles) >= 5:
            return await interaction.client.send(
                interaction,
                f"You cannot add more than `5` default requirements for {channel.mention}.",
                reason="warn",
            )
        if role in required_roles:
            return await interaction.client.send(
                interaction,
                f"That role is already added as a default requirement role for {channel.mention}.",
                reason="warn",
            )

        required_roles.append(role)
        await channel_config.update(
            "required_roles", required_roles, pool=interaction.client.pool
        )

        message = f"Successfully added {role.mention!r} to default requirements roles for {channel.mention}"

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

    @channel.command(name="remove_requirement")
    @app_commands.describe(
        role="Mention a role or enter a role ID.",
        channel="Mention the text channel or enter channel ID.",
    )
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def channel_remove_requirement(
        self,
        interaction: Interaction,
        role: discord.Role,
        channel: Optional[Union[discord.TextChannel, discord.CategoryChannel]] = None,
    ):
        """Remove a default requirement role for some channel."""
        await interaction.response.defer(thinking=True)

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        if channel is None:
            if not isinstance(interaction.channel, discord.TextChannel):
                return await interaction.client.send(
                    interaction,
                    "You cannot use that command in this channel type.",
                    reason="warn",
                    ephemeral=True,
                )
            channel = interaction.channel

        guild_config = await interaction.client.fetch_config(interaction.guild)
        channel_config = await guild_config.get_channel_config(
            channel=channel,
            create_if_not_exists=True,
            pool=interaction.client.pool,
        )

        required_roles = channel_config.required_roles
        if not role in required_roles:
            return await interaction.client.send(
                interaction,
                f"That role is not set as a default requirement role for {channel.mention}.",
                reason="warn",
            )
        required_roles.remove(role)
        await channel_config.update(
            "required_roles", required_roles, pool=interaction.client.pool
        )

        message = f"Successfully removed {role.mention!r} from default requirement roles for {channel.mention}."

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

    @channel.command(name="add_blacklist")
    @app_commands.describe(
        role="Mention a role or enter a role ID.",
        channel="Mention the text channel or enter channel ID.",
    )
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def channel_add_blacklist(
        self,
        interaction: Interaction,
        role: discord.Role,
        channel: Optional[Union[discord.TextChannel, discord.CategoryChannel]] = None,
    ):
        """Add a default blacklist role for some channel."""
        await interaction.response.defer(thinking=True)
        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        if role.id == interaction.guild.id:
            await interaction.client.send(
                interaction,
                "You cannot add `@everyone` role as giveaway blacklist role.",
                reason="warn",
            )

        if channel is None:
            if not isinstance(interaction.channel, discord.TextChannel):
                return await interaction.client.send(
                    interaction,
                    "You cannot use that command in this channel type.",
                    reason="warn",
                    ephemeral=True,
                )
            channel = interaction.channel

        guild_config = await interaction.client.fetch_config(interaction.guild)
        channel_config = await guild_config.get_channel_config(
            channel=channel,
            create_if_not_exists=True,
            pool=interaction.client.pool,
        )

        blacklisted_roles = channel_config.blacklisted_roles
        if len(blacklisted_roles) >= 5:
            return await interaction.client.send(
                interaction,
                f"You cannot add more than `5` default blacklist role for {channel.mention}.",
                reason="warn",
            )
        if role in blacklisted_roles:
            return await interaction.client.send(
                interaction,
                f"That role is already added as a default blacklist role for {channel.mention}.",
                reason="warn",
            )

        blacklisted_roles.append(role)
        await channel_config.update(
            "blacklisted_roles", blacklisted_roles, pool=interaction.client.pool
        )

        message = f"Successfully added {role.mention!r} to default blacklist roles for {channel.mention}."

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

    @channel.command(name="remove_blacklist")
    @app_commands.describe(
        channel="Mention the text channel or enter channel ID.",
        role="Mention a role or enter a role ID.",
    )
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def channel_remove_blacklist(
        self,
        interaction: Interaction,
        role: discord.Role,
        channel: Optional[Union[discord.TextChannel, discord.CategoryChannel]] = None,
    ):
        """Remove a default blacklist role for some channel."""

        await interaction.response.defer(thinking=True)

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        if channel is None:
            if not isinstance(interaction.channel, discord.TextChannel):
                return await interaction.client.send(
                    interaction,
                    "You cannot use that command in this channel type.",
                    reason="warn",
                    ephemeral=True,
                )
            channel = interaction.channel

        guild_config = await interaction.client.fetch_config(interaction.guild)
        channel_config = await guild_config.get_channel_config(
            channel=channel,
            create_if_not_exists=True,
            pool=interaction.client.pool,
        )

        blacklisted_roles = channel_config.blacklisted_roles
        if not role in blacklisted_roles:
            return await interaction.client.send(
                interaction,
                f"That role is not set as a default blacklist role for {channel.mention}.",
                reason="warn",
            )
        blacklisted_roles.remove(role)
        await channel_config.update(
            "blacklisted_roles", blacklisted_roles, pool=interaction.client.pool
        )

        message = f"Successfully removed {role.mention!r} from default blacklist roles for {channel.mention}."

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

    @channel.command(name="add_bypass_roles")
    @app_commands.describe(
        channel="Mention the text channel or enter channel ID.",
        role="Mention a role or enter a role ID.",
    )
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def channel_add_bypass_roles(
        self,
        interaction: Interaction,
        role: discord.Role,
        channel: Optional[Union[discord.TextChannel, discord.CategoryChannel]] = None,
    ):
        """Add a default bypass role for some channel."""
        await interaction.response.defer(thinking=True)

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        if role.id == interaction.guild.id:
            await interaction.client.send(
                interaction, "You can't add `@everyone` role as giveaway bypass role."
            )

        if channel is None:
            if not isinstance(interaction.channel, discord.TextChannel):
                return await interaction.client.send(
                    interaction,
                    "You cannot use that command in this channel type.",
                    reason="warn",
                    ephemeral=True,
                )
            channel = interaction.channel

        guild_config = await interaction.client.fetch_config(interaction.guild)
        channel_config = await guild_config.get_channel_config(
            channel=channel,
            create_if_not_exists=True,
            pool=interaction.client.pool,
        )

        bypass_roles = channel_config.bypass_roles
        if len(bypass_roles) >= 5:
            return await interaction.client.send(
                interaction,
                f"You cannot add more than `5` default bypass roles for {channel.mention}.",
                reason="warn",
            )
        if role in bypass_roles:
            return await interaction.client.send(
                interaction,
                "That role is already added as a default bypass role.",
                reason="warn",
            )

        bypass_roles.append(role)
        await channel_config.update(
            "bypass_roles", bypass_roles, interaction.client.pool
        )

        message = f"Successfully added {role.mention!r} to default bypass roles for {channel.mention}."

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

    @channel.command(name="remove_bypass_roles")
    @app_commands.describe(
        channel="Mention the text channel or enter channel ID.",
        role="Mention a role or enter a role ID.",
    )
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def channel_remove_bypass_roles(
        self,
        interaction: Interaction,
        role: discord.Role,
        channel: Optional[Union[discord.TextChannel, discord.CategoryChannel]] = None,
    ):
        """Remove a default bypass role for some channel."""

        await interaction.response.defer(thinking=True)

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        if channel is None:
            if not isinstance(interaction.channel, discord.TextChannel):
                return await interaction.client.send(
                    interaction,
                    "You cannot use that command in this channel type.",
                    reason="warn",
                    ephemeral=True,
                )
            channel = interaction.channel

        guild_config = await interaction.client.fetch_config(interaction.guild)
        channel_config = await guild_config.get_channel_config(
            channel=channel,
            create_if_not_exists=True,
            pool=interaction.client.pool,
        )

        bypass_roles = channel_config.bypass_roles
        if not role in bypass_roles:
            return await interaction.client.send(
                interaction,
                f"That role is not set as a default bypass role for {channel.mention}.",
                reason="warn",
            )
        bypass_roles.remove(role)
        await channel_config.update(
            "bypass_roles", bypass_roles, interaction.client.pool
        )

        message = f"Successfully removed {role.mention!r} from default bypass roles for {channel.mention}."

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

    @channel.command(name="multiplier_entries")
    @app_commands.describe(
        role="Mention a role or enter a role ID.",
        entries="The number of multiplier entries for the role. Enter 1 to reset.",
        channel="Mention the text channel or enter channel ID.",
    )
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def channel_multiplier_entries(
        self,
        interaction: Interaction,
        role: discord.Role,
        entries: app_commands.Range[int, 1, 5],
        channel: Optional[Union[discord.TextChannel, discord.CategoryChannel]] = None,
    ):
        """Edit multiplier entries of a role."""

        await interaction.response.defer(thinking=True)

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        if role.id == interaction.guild.id:
            return await interaction.client.send(
                interaction, "You can't add multiplier entries to `@everyone` role."
            )

        if channel is None:
            if not isinstance(interaction.channel, discord.TextChannel):
                return await interaction.client.send(
                    interaction,
                    "You cannot use that command in this channel type.",
                    reason="warn",
                    ephemeral=True,
                )
            channel = interaction.channel

        guild_config = await interaction.client.fetch_config(interaction.guild)
        channel_config = await guild_config.get_channel_config(
            channel=channel,
            create_if_not_exists=True,
            pool=interaction.client.pool,
        )

        multiplier_roles = channel_config.multiplier_roles
        if len(multiplier_roles) >= 5:
            return await interaction.client.send(
                interaction,
                f"You cannot add more than `5` default multiplier entry roles for {channel.mention}.",
                reason="warn",
            )
        if entries == 1:
            if role in multiplier_roles:
                multiplier_roles.pop(role)
            else:
                return await interaction.client.send(
                    interaction,
                    f"That role doesn't have any default extra multiplier entries for {channel.mention}.",
                    reason="warn",
                )
        else:
            multiplier_roles[role] = entries
        await channel_config.update(
            "multiplier_roles", multiplier_roles, interaction.client.pool
        )

        message = f"Successfully set {role.mention}'s multiplier entries to `{entries}` for {channel.mention}."

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

    @channel.command(name="ping")
    @app_commands.describe(
        role="Mention a role or enter a role ID.",
        channel="Mention the text channel or enter channel ID.",
    )
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def channel_ping(
        self,
        interaction: Interaction,
        role: discord.Role,
        channel: Optional[Union[discord.TextChannel, discord.CategoryChannel]] = None,
    ):
        """Edit ping role of a channel."""

        await interaction.response.defer(thinking=True)

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        if role.id == interaction.guild.id:
            return await interaction.client.send(
                interaction, "You can't set @everyone role as the ping role."
            )

        if channel is None:
            if not isinstance(interaction.channel, discord.TextChannel):
                return await interaction.client.send(
                    interaction,
                    "You cannot use that command in this channel type.",
                    reason="warn",
                    ephemeral=True,
                )
            channel = interaction.channel

        guild_config = await interaction.client.fetch_config(interaction.guild)
        channel_config = await guild_config.get_channel_config(
            channel=channel,
            create_if_not_exists=True,
            pool=interaction.client.pool,
        )

        await channel_config.update("ping", role, interaction.client.pool)

        message = (
            f"Successfully set {role.mention}'s to ping role for {channel.mention}."
        )

        await interaction.client.send(
            interaction,
            message,
            "success",
        )

    @channel.command(name="clear")
    @app_commands.describe(
        channel="Mention the text channel or enter channel ID.",
    )
    @app_commands.checks.cooldown(1, 15, key=lambda i: (i.guild, i.user.id))
    async def channel_clear(
        self,
        interaction: Interaction,
        channel: Optional[Union[discord.TextChannel, discord.CategoryChannel]] = None,
    ):
        """Clear the settings for some channel."""

        await interaction.response.defer(thinking=True)

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        if channel is None:
            if not isinstance(interaction.channel, discord.TextChannel):
                return await interaction.client.send(
                    interaction,
                    "You cannot use that command in this channel type.",
                    reason="warn",
                    ephemeral=True,
                )
            channel = interaction.channel

        guild_config = await interaction.client.fetch_config(interaction.guild)
        channel_config = await guild_config.get_channel_config(
            channel=channel,
            create_if_not_exists=False,
            pool=interaction.client.pool,
        )

        if channel_config:
            await channel_config.delete(
                channel.id, interaction.guild.id, interaction.client.pool
            )
            guild_config.channel_settings.remove(channel_config)
            await interaction.client.send(
                interaction, "Successfully cleared settings for that channel."
            )
        else:
            await interaction.client.send(
                interaction,
                "The channel doesn't have any configuration setup.",
                reason="warn",
            )

    @channel.command(name="view")
    @app_commands.describe(
        channel="Mention the text channel or enter channel ID.",
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild, i.user.id))
    async def view(
        self,
        interaction: Interaction,
        channel: Optional[Union[discord.TextChannel, discord.CategoryChannel]] = None,
    ):
        """View the giveaway settings for the given channel."""

        await interaction.response.defer(thinking=True)

        assert isinstance(interaction.user, discord.Member)
        assert interaction.guild is not None

        if channel is None:
            if not isinstance(interaction.channel, discord.TextChannel):
                return await interaction.client.send(
                    interaction,
                    "You cannot use that command in this channel type.",
                    reason="warn",
                    ephemeral=True,
                )
            channel = interaction.channel

        guild_config = await interaction.client.fetch_config(interaction.guild)
        channel_config = await guild_config.get_channel_config(
            channel=channel, create_if_not_exists=False, pool=interaction.client.pool
        )
        if channel_config is None:
            return await interaction.client.send(
                interaction,
                "No configuration found for that channel in the database.",
                reason="warn",
                ephemeral=True,
            )

        embed = discord.Embed(
            title=f"{SETTINGS_EMOJI} Giveaway Settings for {channel.name}",
            colour=guild_config.color,
            timestamp=datetime.datetime.now(),
        )
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon)

        embed.add_field(
            name="Default Required Roles",
            value=f"{BLANK_SPACE}{ARROW_EMOJI} {','.join(role.mention for role in channel_config.required_roles if role is not None) if channel_config.required_roles else 'None'}\n",
            inline=False,
        )
        embed.add_field(
            name="Default Blacklisted Roles",
            value=f"{BLANK_SPACE}{ARROW_EMOJI} {','.join(role.mention for role in channel_config.blacklisted_roles if role is not None) if channel_config.blacklisted_roles else 'None'}\n",
            inline=False,
        )
        embed.add_field(
            name="Default Bypass Roles",
            value=f"{BLANK_SPACE}{ARROW_EMOJI} {','.join(role.mention for role in channel_config.bypass_roles if role is not None) if channel_config.bypass_roles else 'None'}\n",
            inline=False,
        )
        embed.add_field(
            name="Default Bonus Entry Roles",
            value=f"{BLANK_SPACE}{ARROW_EMOJI} {','.join(f'{role.mention}: {multiplier_roles}' for role, multiplier_roles in channel_config.multiplier_roles.items() if role is not None) if channel_config.multiplier_roles else 'None'}",
            inline=False,
        )

        await interaction.followup.send(embed=embed)

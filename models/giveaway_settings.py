from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union, overload

import asyncpg
import discord

from utils.exceptions import MaxChannelConfigCreationError

log = logging.getLogger(__name__)

__all__: Tuple[str, ...] = (
    "ChannelConfig",
    "GuildConfig",
)


class GuildConfigData(TypedDict):
    guild: int
    logging: Optional[int]
    ping: Optional[int]
    reaction: str
    participants_reaction: str
    required_roles: List[int]
    bypass_roles: List[int]
    multiplier_roles: Dict[int, int]
    managers: List[int]
    dm_winner: bool
    dm_host: bool
    color: int
    button_style: str
    end_message: str
    reroll_message: str
    dm_message: str
    dm_host_message: str
    gw_header: str
    gw_end_header: str


class ChannelConfig:
    """Represents the configuration settings for a channel.

    Attributes
    ----------
    channel: Union[discord.TextChannel, discord.CategoryChannel]
        The channel associated with the config.
    guild: discord.Guild
        The guild to which the channel belongs.
    required_roles: List[discord.Role]
        The list of default required roles.
    blacklisted_roles: List[discord.Role]
        The list of default blacklisted roles.
    bypass_roles: List[discord.Role]
        The list of default bypass_roles.
    multiplier_roles: Dict[discord.Role, int]
        The role and number of multiplier_roles entries mapping.
    ping: Optional[discord.Role]
        The default ping role for some channel.
    """

    __slots__: Tuple[str, ...] = (
        "channel",
        "guild",
        "required_roles",
        "blacklisted_roles",
        "bypass_roles",
        "multiplier_roles",
        "ping",
    )

    def __init__(
        self,
        channel: Union[discord.TextChannel, discord.CategoryChannel],
        guild: discord.Guild,
        *,
        required_roles: List[discord.Role],
        blacklisted_roles: List[discord.Role],
        bypass_roles: List[discord.Role],
        multiplier_roles: Dict[discord.Role, int],
        ping: Optional[discord.Role] = None,
    ):
        self.channel = channel
        self.guild = guild
        self.required_roles = required_roles
        self.blacklisted_roles = blacklisted_roles
        self.bypass_roles = bypass_roles
        self.multiplier_roles = multiplier_roles
        self.ping = ping

    def __repr__(self):
        return f"<ChannelConfig channel={self.channel!r}>"

    @classmethod
    def from_data(
        cls,
        guild: discord.Guild,
        data: asyncpg.Record,
    ) -> Optional["ChannelConfig"]:
        """Create a ChannelConfig object from given data.

        Parameters
        ----------
        guild: discord.Guild
            The guild to which the channel belongs.
        value: Any
            The new value for the column.

        Returns
        -------
        ChannelConfig
            The updated `ChannelConfig` instance.
        """

        data = dict(data)

        # We do not need these
        channel_id = data.pop("channel")
        channel = guild.get_channel(channel_id)
        if channel is None:
            return

        assert isinstance(channel, (discord.TextChannel, discord.CategoryChannel))

        data["ping"] = guild.get_role(data["ping"])
        data["required_roles"] = [guild.get_role(role) for role in data["required_roles"] if role is not None]
        data["blacklisted_roles"] = [guild.get_role(role) for role in data["blacklisted_roles"] if role is not None]
        data["bypass_roles"] = [guild.get_role(role) for role in data["bypass_roles"] if role is not None]
        data["multiplier_roles"] = {
            guild.get_role(role): multiplier_roles
            for role, multiplier_roles in data["multiplier_roles"].items()
            if role is not None
        }

        data.pop("guild")

        return cls(channel, guild, **data)

    async def update(self, column: str, value: Any, pool: asyncpg.Pool) -> "ChannelConfig":
        """Update the specified column with the provided value in the database.

        Parameters
        ----------
        column: str
            The column to be updated.
        value: Any
            The new value for the column.
        pool: asyncpg.Pool
            The database connection pool.

        Raises
        ------
        ValueError
            If the provided column is not a valid column name in `self.__slots__`.

        Returns
        -------
        ChannelConfig
            The updated `ChannelConfig` instance.
        """
        if column not in self.__slots__:
            raise ValueError(f"Invalid column: {column}")

        setattr(self, column, value)

        if isinstance(value, list):
            value = [role.id for role in value if role is not None]
        elif isinstance(value, dict):
            value = {role.id: multiplier_roles for role, multiplier_roles in value.items() if role is not None}
        elif isinstance(value, discord.Role):
            value = value.id
        else:
            raise ValueError("Unknown type given.")

        query = f"""INSERT INTO channel_configs (guild, channel, {column}) VALUES ($1, $2, $3)
                    ON CONFLICT (guild, channel) DO
                    UPDATE SET {column} = excluded.{column}"""

        await pool.execute(
            query,
            self.guild.id,
            self.channel.id,
            value,
        )

        return self

    @classmethod
    async def create(
        cls,
        guild: discord.Guild,
        channel: Union[discord.TextChannel, discord.CategoryChannel],
        pool: asyncpg.Pool,
    ) -> "ChannelConfig":
        query = """INSERT INTO channel_configs (guild, channel) VALUES ($1, $2) RETURNING *"""

        record = await pool.fetchrow(
            query,
            guild.id,
            channel.id,
        )

        instance = cls.from_data(guild, record)
        assert instance is not None  # Since we just created it.
        return instance

    @staticmethod
    async def delete(channel_id: int, guild_id: int, pool: asyncpg.Pool):
        """Delete the current ChannelConfig object.

        Parameters
        ----------
        channel_id: int
            The ID of the channel.
        guild_id: int
            The ID of the guild.
        pool: asyncpg.Pool
            The database connection pool.
        """

        query = """DELETE FROM channel_configs
                    WHERE guild = $ AND channel = $2"""

        await pool.execute(query, guild_id, channel_id)


class GuildConfig:
    """Represents the configuration settings for a guild.

    Parameters
    ----------
    guild: discord.Guild
        The guild associated with the configuration.
    logging: Optional[discord.TextChannel]
        The logging text channel for the guild.
    ping: Optional[discord.Role]
        The role to ping for notifications.
    reaction: str
        The reaction used for giveaways.
    participants_reaction,: str
        The reaction used for giveaways participants button.
    required_roles: List[discord.Role]
        The default roles required to join giveaway.
    blacklisted_roles: List[discord.Role]
        The default roles blacklisted from joining a giveaway.
    bypass_roles: List[discord.Role]
        The roles that bypass_roles certain restrictions.
    multiplier_roles: Dict[discord.Role, int]
        The multiplier_roles points assigned to each role.
    managers: List[discord.Role]
        The roles with manager permissions.
    dm_winner: bool
        Whether to send a direct message to the winner.
    dm_host: bool
        Whether to send a direct message to the host.
    channel_settings: List[ChannelConfig]
        The settings for each channel.
    color: discord.Colour
        The color used for messages.
    button_style: discord.ButtonStyle
        The style of the button.
    end_message: str
        The message sent when a giveaway ends.
    reroll_message: str
        The message sent when a giveaway rerolls.
    dm_message: str
        The direct message sent to winner.
    dm_host_message: str
        The direct message sent to host.
    gw_header: str
        The header for the giveaway message.
    gw_end_header: str
        The header for the giveaway end.
    """

    __slots__: Tuple[str, ...] = (
        "guild",
        "logging",
        "ping",
        "reaction",
        "participants_reaction",
        "required_roles",
        "blacklisted_roles",
        "bypass_roles",
        "multiplier_roles",
        "managers",
        "dm_winner",
        "dm_host",
        "channel_settings",
        "color",
        "button_style",
        "end_message",
        "reroll_message",
        "dm_message",
        "dm_host_message",
        "gw_header",
        "gw_end_header",
    )

    def __init__(
        self,
        guild: discord.Guild,
        *,
        logging: Optional[discord.TextChannel],
        ping: Optional[discord.Role],
        reaction: str,
        participants_reaction: str,
        required_roles: List[discord.Role],
        blacklisted_roles: List[discord.Role],
        bypass_roles: List[discord.Role],
        multiplier_roles: Dict[discord.Role, int],
        managers: List[discord.Role],
        dm_winner: bool,
        dm_host: bool,
        channel_settings: List[ChannelConfig],
        color: discord.Colour,
        button_style: discord.ButtonStyle,
        end_message: str,
        reroll_message: str,
        dm_message: str,
        dm_host_message: str,
        gw_header: str,
        gw_end_header: str,
    ):
        self.guild = guild
        self.logging = logging
        self.ping = ping
        self.reaction = reaction
        self.participants_reaction = participants_reaction
        self.required_roles = required_roles
        self.blacklisted_roles = blacklisted_roles
        self.bypass_roles = bypass_roles
        self.multiplier_roles = multiplier_roles
        self.managers = managers
        self.dm_winner = dm_winner
        self.dm_host = dm_host
        self.channel_settings = channel_settings
        self.color = color
        self.button_style = button_style
        self.end_message = end_message
        self.reroll_message = reroll_message
        self.dm_host_message = dm_host_message
        self.dm_message = dm_message
        self.gw_header = gw_header
        self.gw_end_header = gw_end_header

    def __repr__(self):
        return f"<GuildConfig guild={self.guild!r}>"

    @staticmethod
    async def _create_config(guild_id: int, pool: asyncpg.Pool) -> asyncpg.Record:
        return await pool.fetchrow(
            "INSERT INTO configs (guild) VALUES ($1) RETURNING *",
            guild_id,
        )

    @classmethod
    def _from_data(
        cls,
        guild: discord.Guild,
        data: asyncpg.Record,
        channel_data: List[asyncpg.Record],
    ) -> "GuildConfig":
        data = dict(data)
        data["color"] = discord.Colour(data["color"])

        data["logging"] = guild.get_channel(data["logging"])
        data["ping"] = guild.get_role(data["ping"])
        data["required_roles"] = [guild.get_role(role) for role in data["required_roles"] if role is not None]
        data["blacklisted_roles"] = [guild.get_role(role) for role in data["blacklisted_roles"] if role is not None]
        data["bypass_roles"] = [guild.get_role(role) for role in data["bypass_roles"] if role is None]
        data["multiplier_roles"] = {
            guild.get_role(role): multiplier
            for role, multiplier in data["multiplier_roles"].items()
            if role is not None and multiplier > 1
        }
        data["managers"] = [guild.get_role(role) for role in data["managers"] if role is not None]

        data["button_style"] = discord.utils.get(discord.ButtonStyle, value=data["button_style"])

        data["channel_settings"] = [
            channel_setting for record in channel_data if (channel_setting := ChannelConfig.from_data(guild, record))
        ]

        data.pop("guild")  # We do not need this.

        return cls(guild, **data)

    def to_dict(self) -> GuildConfigData:
        """Converts this GuildConfig object into a dict."""

        data = GuildConfigData(
            guild=self.guild.id,
            reaction=self.reaction,
            participants_reaction=self.participants_reaction,
            required_roles=[role.id for role in self.required_roles if role is not None],
            blacklisted_roles=[role.id for role in self.blacklisted_roles if role is not None],
            bypass_roles=[role.id for role in self.bypass_roles if role is not None],
            multiplier_roles={
                role.id: multiplier_roles for role, multiplier_roles in self.multiplier_roles.items() if role is not None
            },
            managers=[role.id for role in self.managers if role is not None],
            dm_winner=self.dm_winner,
            dm_host=self.dm_host,
            color=int(self.color),
            button_style=self.button_style.value,
            end_message=self.end_message,
            reroll_message=self.reroll_message,
            dm_message=self.dm_message,
            dm_host_message=self.dm_host_message,
            gw_header=self.gw_header,
            gw_end_header=self.gw_end_header,
        )  # type: ignore
        if self.logging:
            data["logging"] = self.logging.id
        if self.ping:
            data["ping"] = self.ping.id
        return data

    @classmethod
    async def fetch(cls, guild: discord.Guild, pool: asyncpg.Pool) -> "GuildConfig":
        """Create a GuildConfig instance from data retrieved from a database.

        Parameters
        ----------
        guild: discord.Guild
            The discord guild.
        pool: asyncpg.Pool
            The database connection pool.

        Returns
        -------
        GuildConfig
            An instance of GuildConfig populated with the retrieved data.
        """

        data = await pool.fetchrow("SELECT * FROM configs WHERE guild = $1", guild.id)
        channel_data: List[asyncpg.Record] = await pool.fetch("SELECT * FROM channel_configs WHERE guild = $1", guild.id)

        if not data:
            data: asyncpg.Record = await cls._create_config(guild.id, pool)

        return cls._from_data(guild, data, channel_data)

    async def update(self, column: str, value: Any, pool: asyncpg.Pool) -> "GuildConfig":
        """Update the specified column with the provided value in the database.

        Parameters
        ----------
        column: str
            The column to be updated.
        value: Any
            The new value for the column.
        pool: asyncpg.Pool
            The database connection pool.

        Raises
        ------
        ValueError
            If the provided column is not a valid column name in `self.__slots__`.

        Returns
        -------
        GuildConfig
            The updated `GuildConfig` instance.
        """
        if column not in self.__slots__:
            raise ValueError(f"Invalid column: {column}")

        setattr(self, column, value)

        data = self.to_dict()

        columns = ", ".join(data.keys())
        placeholders = ", ".join([f"${i + 1}" for i in range(len(data))])
        update_clause = ", ".join([f"{key} = EXCLUDED.{key}" for key in data if key != "guild"])

        query = f"""
            INSERT INTO configs ({columns})
            VALUES ({placeholders})
            ON CONFLICT (guild) DO
            UPDATE SET {update_clause}
        """

        values = list(data.values())
        await pool.execute(query, *values)
        return self

    @overload
    async def get_channel_config(
        self,
        channel: Union[discord.TextChannel, discord.CategoryChannel],
        create_if_not_exists: bool = True,
        pool: Optional[asyncpg.Pool] = None,
    ) -> ChannelConfig:
        ...

    @overload
    async def get_channel_config(
        self,
        channel: Union[discord.TextChannel, discord.CategoryChannel],
        create_if_not_exists: bool = False,
        pool: Optional[asyncpg.Pool] = None,
    ) -> Optional[ChannelConfig]:
        ...

    async def get_channel_config(
        self,
        channel: Union[discord.TextChannel, discord.CategoryChannel],
        create_if_not_exists: bool = True,
        pool: Optional[asyncpg.Pool] = None,
    ) -> Optional[ChannelConfig]:
        """
        Retrieves the configuration for a specific channel.

        Parameters
        ----------
        channel: Union[discord.TextChannel, discord.CategoryChannel]
            The channel for which to retrieve the configuration.
        create_if_not_exists: Optional[bool]
            Whether to create a new configuration if it doesn't exist. Default is True.
        pool: Optional[asyncpg.Pool]
            The connection pool for interacting with the database.

        Returns
        -------
        Optional[ChannelConfig]
            The ChannelConfig object if it exists, or None if it doesn't exist and create_if_not_exists is set to False.

        Raises
        ------
        MaxChannelConfigCreationError
            If create_if_not_exists is True and the maximum number of channel configurations has already been reached.
        """

        config = discord.utils.get(self.channel_settings, channel=channel)
        if config is not None:
            return config

        if create_if_not_exists:
            if len(self.channel_settings) >= 25:
                raise MaxChannelConfigCreationError()
            else:
                if pool:
                    config = await ChannelConfig.create(channel.guild, channel, pool)
                    self.channel_settings.append(config)
                    return config

        return None

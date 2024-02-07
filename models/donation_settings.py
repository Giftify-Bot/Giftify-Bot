from __future__ import annotations

from enum import Enum
from typing import Optional, Union

import asyncpg
import discord

from core.bot import Giftify

__all__: tuple[str, ...] = ("GuildDonationConfig", "DonationAction")


class DonationAction(Enum):
    ADD = 0
    REMOVE = 1
    SYNC = 2

    def __str__(self) -> str:
        if self == DonationAction.ADD:
            return "Added"
        elif self == DonationAction.REMOVE:
            return "Remove"
        else:
            return "Synced"


class GuildDonationConfig:
    """Represents the donation configuration settings for a guild.

    Parameters
    ----------
    bot: Giftify
        The bot instance handling the configuration.
    guild  discord.Guild
        The guild associated with the configuration.
    category: str
        The category or name of the donation configuration.
    symbol: str
        The symbol or identifier of the donation category.
    roles: Dict[int, discord.Role]
        A dictionary mapping of amount to `discord.Role`.
    managers: List[discord.Role]
        A list of `discord.Role` objects representing the roles with donation management permissions.
    logging: Optional[discord.TextChannel]
        An optional `discord.TextChannel` object used for logging donation events.
    """

    __slots__: tuple[str, ...] = (
        "bot",
        "guild",
        "category",
        "symbol",
        "roles",
        "managers",
        "logging",
    )

    def __init__(
        self,
        bot: Giftify,
        *,
        guild: discord.Guild,
        category: str,
        symbol: str,
        roles: dict[int, discord.Role],
        managers: list[discord.Role],
        logging: Optional[discord.TextChannel] = None,
    ) -> None:
        self.bot = bot
        self.guild = guild
        self.category = category
        self.symbol = symbol
        self.roles = roles
        self.managers = managers
        self.logging = logging

    def __str__(self) -> str:
        return self.category

    def __repr__(self) -> str:
        return f"<GuildDonationConfig guild={self.guild!r}> category={self.category}"

    @classmethod
    async def create(cls, guild_id: int, category: str, bot: Giftify, *, symbol: Optional[str] = None) -> GuildDonationConfig:
        record = await bot.pool.fetchrow(
            "INSERT INTO donation_configs (guild, category, symbol) VALUES ($1, $2, $3) RETURNING *",
            guild_id,
            category,
            symbol,
        )
        instance = await cls.from_record(bot, record=record)
        assert instance is not None
        return instance

    @classmethod
    async def from_record(cls, bot: Giftify, *, record: asyncpg.Record) -> Optional[GuildDonationConfig]:
        guild = bot.get_guild(record["guild"])
        if not guild:
            return None

        category = record["category"]
        symbol = record["symbol"]
        roles = {int(amount): role for amount, role_id in record["roles"].items() if (role := guild.get_role(role_id))}
        managers = [role for role_id in record["managers"] if (role := guild.get_role(role_id))]
        logging: Optional[discord.TextChannel] = guild.get_channel(record["logging"]) if record["logging"] else None  # type: ignore

        return cls(
            bot,
            guild=guild,
            category=category,
            symbol=symbol,
            roles=roles,
            managers=managers,
            logging=logging,
        )

    async def update(
        self,
        key: str,
        value: Union[str, discord.TextChannel, dict[int, discord.Role], list[discord.Role]],
    ) -> None:
        """
        Update a specific attribute of the GuildDonationConfig.

        Parameters
        ----------
        key: str
            The attribute name to be updated. Should be one of "category", "symbol", "logging", "roles", or "managers".
        value: Union[str, discord.TextChannel, Dict[int, discord.Role], List[discord.Role]]
            The new value for the attribute.

        Raises
        ------
        ValueError
            If an invalid key is provided.
            If the value is not of the expected type for the specified key.

        Returns
        -------
        None
        """
        if key not in {"category", "symbol", "logging", "roles", "managers"}:
            msg = "Invalid key provided. Valid keys are 'category', 'symbol', 'logging', 'roles', and 'managers'."
            raise ValueError(msg)

        if key in {"category", "symbol"}:
            await self._update_config(key, str(value))
            setattr(self, key, value)
        elif key == "logging":
            if not isinstance(value, discord.TextChannel):
                msg = "Value for 'logging' must be a discord.TextChannel."
                raise ValueError(msg)
            self.logging = value

            await self._update_config(key, value.id)
        elif key == "roles":
            if not isinstance(value, dict):
                msg = "Value for 'roles' must be a dictionary."
                raise ValueError(msg)
            self.roles = value
            role_values = {amount: role.id for amount, role in value.items()}
            await self._update_config(key, role_values)
        elif key == "managers":
            if not isinstance(value, list):
                msg = "Value for 'managers' must be a list."
                raise ValueError(msg)
            self.managers = value
            role_ids = [role.id for role in value]
            await self._update_config(key, role_ids)

    async def _update_config(self, key: str, value: Union[str, int, list[int], dict[int, int]]) -> None:
        await self.bot.pool.execute(
            f"UPDATE donation_configs SET {key} = $1 WHERE guild = $2 AND category = $3",
            value,
            self.guild.id,
            self.category,
        )

    async def delete(self) -> None:
        await self.bot.pool.execute(
            "DELETE FROM donation_configs WHERE guild = $1 AND category = $2",
            self.guild.id,
            self.category,
        )

    async def reset(self) -> None:
        await self.bot.pool.execute(
            "DELETE FROM donations WHERE guild = $1 AND category = $2",
            self.guild.id,
            self.category,
        )

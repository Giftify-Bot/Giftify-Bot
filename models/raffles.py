from __future__ import annotations

import random
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import asyncpg
import discord

from utils.exceptions import RaffleError
from utils.functions import MemberProxy, filter_none

if TYPE_CHECKING:
    from core.bot import Giftify


class Raffle:
    """
    Represents a raffle object.

    Attributes
    ----------
    pool: asyncpg.Pool
        The PostgreSQL connection pool instance.
    guild: discord.Guild
        The guild (server) where the raffle is hosted.
    name: str
        The name of the raffle.
    winner: Optional[discord.Member]
        The member instance of the winner, or None if the raffle hasn't ended yet.
    deputy_roles: List[discord.Role]
        A list of roles associated with the raffle.
    deputy_members: List[discord.Member]
        A list of members associated with the raffle.
    tickets: Dict[discord.Member, int]
        A mapping of members to the number of tickets they have.
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        guild: discord.Guild,
        name: str,
        winner: Optional[discord.Member],
        deputy_roles: List[discord.Role],
        deputy_members: List[discord.Member],
        tickets: Dict[discord.Member, int],
    ) -> None:
        self.pool = pool

        self.guild = guild
        self.name = name
        self.winner = winner
        self.deputy_roles = deputy_roles
        self.deputy_members = deputy_members
        self.tickets = tickets

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"<Raffle name={self.name} guild={self.guild} winner={self.winner}>"

    def __hash__(self) -> int:
        return hash((self.name, self.guild))

    def __eq__(self, other: Raffle) -> bool:
        return self.name == other.name and self.guild == other.guild

    @classmethod
    async def from_record(cls, bot: Giftify, *, record: asyncpg.Record) -> Raffle:
        name = record["name"]
        guild = bot.get_guild(record["guild"])
        if guild is None:
            msg = "The guild having the raffle was not found."
            raise RaffleError(msg)

        winner_id = record["winner"]
        winner: Optional[discord.Member] = (
            (await bot.get_or_fetch_member(guild, winner_id) or MemberProxy(winner_id)) if winner_id else None
        )  # type: ignore

        deputy_roles = [guild.get_role(role_id) for role_id in record["deputy_roles"]]
        deputy_members = [await bot.get_or_fetch_member(guild, member_id) for member_id in record["deputy_members"]]

        tickets = {
            await bot.get_or_fetch_member(guild, int(member_id)): num_tickets
            for member_id, num_tickets in record["tickets"].items()
        }

        return cls(
            bot.pool,
            guild=guild,
            name=name,
            winner=winner,
            deputy_roles=filter_none(deputy_roles),
            deputy_members=filter_none(deputy_members),
            tickets=filter_none(tickets),
        )

    async def roll(self) -> discord.Member:
        """
        End the raffle and set the winner.
        """
        members = list(self.tickets.keys())
        weights = list(self.tickets.values())

        self.winner = random.choices(members, weights, k=1)[0]

        await self.save()

        return self.winner

    async def add_deputy(self, obj: Union[discord.Member, discord.Role]) -> None:
        """
        Add a deputy to the raffle.

        Parameters
        ----------
        obj: Union[discord.Member, discord.Role]
            The instance of deputy member or role to be added.
        """

        if isinstance(obj, discord.Member):
            if len(self.deputy_members) >= 25:
                msg = "You cannot add more than 25 deputy members."
                raise RaffleError(msg)
            self.deputy_members.append(obj)
        elif isinstance(obj, discord.Role):
            if len(self.deputy_roles) >= 10:
                msg = "You cannot add more than 10 deputy roles."
                raise RaffleError(msg)
            self.deputy_roles.append(obj)
        else:
            msg = "Invalid obj type."
            raise RaffleError(msg)

        await self.save()

    async def remove_deputy(self, obj: Union[discord.Member, discord.Role]) -> None:
        """
        Remove a deputy from the raffle.

        Parameters
        ----------
        obj: Union[discord.Member, discord.Role]
            The instance of deputy member or role to be removed.
        """
        if isinstance(obj, discord.Member):
            if obj not in self.deputy_members:
                msg = "That member is not a deputy."
                raise RaffleError(msg)
            self.deputy_members.remove(obj)
        elif isinstance(obj, discord.Role):
            if obj not in self.deputy_roles:
                msg = "That role is not a deputy."
                raise RaffleError()
            self.deputy_roles.remove(obj)
        else:
            msg = "Invalid obj type."
            raise RaffleError(msg)

        await self.save()

    async def add_tickets(self, member: discord.Member, num_tickets: int) -> None:
        """
        Add tickets to a member.

        Parameters
        ----------
        member: discord.Member
            The instance of the member.
        num_tickets: int
            The number of tickets to add.
        """
        if member in self.tickets:
            self.tickets[member] += num_tickets
        else:
            self.tickets[member] = num_tickets

        await self.save()

    async def remove_tickets(self, member: discord.Member, num_tickets: int) -> None:
        """
        Remove tickets from a member.

        Parameters
        ----------
        member: discord.Member
            The instance of the member.
        num_tickets: int
            The number of tickets to remove.
        """
        if member in self.tickets:
            self.tickets[member] -= num_tickets
            if self.tickets[member] <= 0:
                del self.tickets[member]

            await self.save()
        else:
            msg = f"That member does not have any tickets in {self.name} raffle."
            raise RaffleError(msg)

    async def save(self) -> None:
        """
        Update raffle attributes in the database.
        """
        query = """
            INSERT INTO raffles (guild, name, winner, deputy_roles, deputy_members, tickets)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (guild, name)
            DO UPDATE SET winner = EXCLUDED.winner, deputy_roles = EXCLUDED.deputy_roles,
                          deputy_members = EXCLUDED.deputy_members, tickets = EXCLUDED.tickets;
        """
        await self.pool.execute(
            query,
            self.guild.id,
            self.name,
            self.winner.id if self.winner else None,
            [role.id for role in self.deputy_roles if role is not None],
            [member.id for member in self.deputy_members if member is not None],
            {str(member.id): num_tickets for member, num_tickets in self.tickets.items() if member is not None},
        )

    async def delete(self) -> None:
        """
        Delete the  raffle from the database.
        """
        query = """DELETE FROM raffles WHERE guild = $1 AND name = $2"""
        await self.pool.execute(query, self.guild.id, self.name)

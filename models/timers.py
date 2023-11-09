from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import asyncpg

if TYPE_CHECKING:
    from typing_extensions import Self


class Timer:
    """
    Represents a timer object.

    Attributes
    ----------
    message_id: int
        The ID of the associated message.
    channel_id: int
        The ID of the channel where the timer was created.
    guild_id: int
        The ID of the guild (server) where the timer was created.
    author_id: int
        The ID of the author who created the timer.
    event: str
        The event to trigger when timer ends.
    title: str
        The title of the timer.
    expires: datetime.datetime
        The expiration date and time of the timer.
    """

    __slots__ = (
        "message_id",
        "channel_id",
        "guild_id",
        "author_id",
        "event",
        "title",
        "expires",
    )

    def __init__(
        self,
        *,
        message_id: int,
        channel_id: int,
        guild_id: int,
        author_id: int,
        event: str,
        title: str,
        expires: datetime.datetime,
    ):
        self.message_id = message_id
        self.channel_id = channel_id
        self.guild_id = guild_id
        self.author_id = author_id
        self.event = event
        self.title = title
        self.expires = expires

    def __eq__(self, other: "Timer") -> bool:
        try:
            return self.message_id == other.message_id
        except AttributeError:
            return False

    def __hash__(self) -> int:
        return hash(self.message_id)

    def __repr__(self) -> str:
        return f"<Timer expires={self.expires}>"

    @classmethod
    def from_record(cls, *, record: asyncpg.Record) -> "Timer":
        """
        Create a Timer object from a database record.

        Parameters
        ----------
        record: asyncpg.Record
            The record retrieved from the database.

        Returns
        -------
        Timer
            The Timer object created from the record.
        """
        return cls(
            message_id=record["message"],
            channel_id=record["channel"],
            guild_id=record["guild"],
            author_id=record["author_id"],
            event=record["event"],
            title=record["title"],
            expires=record["expires"],
        )

    @classmethod
    async def create(
        cls,
        message_id: int,
        channel_id: int,
        guild_id: int,
        author_id: int,
        event: str,
        title: str,
        expires: datetime.datetime,
        pool: asyncpg.Pool,
    ) -> "Timer":
        """
        Create a new Timer object and insert it into the database.

        Parameters
        ----------
        message_id: int
            The ID of the message associated with the timer.
        channel_id: int
            The ID of the channel where the timer was created.
        guild_id: int
            The ID of the guild (server) where the timer was created.
        author_id: int
            The ID of the author who created the timer.
        event: str
            The name of the timer event.
        title: str
            The title of the timer.
        expires: datetime.datetime
            The expiration date and time of the timer.
        pool: asyncpg.Pool
            The connection pool to use for database operations.

        Returns
        -------
        Timer
            The created Timer object.
        """
        query = """INSERT INTO timers (message, channel, guild, author_id, event, title, expires) 
                   VALUES ($1, $2, $3, $4, $5, $6, $7) 
                   RETURNING *"""
        record = await pool.fetchrow(
            query,
            message_id,
            channel_id,
            guild_id,
            author_id,
            event,
            title,
            expires,
        )
        return cls.from_record(record=record)

    async def end(self, pool: asyncpg.Pool) -> None:
        """
        End the timer by removing it from the database.

        Parameters
        ----------
        pool: asyncpg.Pool
            The connection pool to use for database operations.
        """
        await pool.execute(
            "DELETE FROM timers WHERE guild = $1 AND channel = $2 AND message = $3",
            self.guild_id,
            self.channel_id,
            self.message_id,
        )

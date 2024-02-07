from __future__ import annotations

from typing import TYPE_CHECKING, Any

import orjson

if TYPE_CHECKING:
    import asyncpg

__all__ = ("db_init",)


def _encode_jsonb(value: Any) -> str:
    if isinstance(value, dict):
        value = {str(key): val for key, val in value.items() if isinstance(key, str)}
    return orjson.dumps(value).decode("utf-8")



def _decode_jsonb(value: str) -> Any:
    return orjson.loads(value)


async def db_init(connection: asyncpg.Connection) -> None:
    await connection.set_type_codec("jsonb", schema="pg_catalog", encoder=_encode_jsonb, decoder=_decode_jsonb)

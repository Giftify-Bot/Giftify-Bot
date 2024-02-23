from __future__ import annotations

from typing import TYPE_CHECKING, Any

import orjson

if TYPE_CHECKING:
    import asyncpg

__all__ = ("db_init",)


def _encode_jsonb(value: Any) -> str:
    if isinstance(value, dict):
        value = {str(key): val for key, val in value.items()}
    return orjson.dumps(value).decode("utf-8")


def _decode_jsonb(value: str) -> Any:
    val = orjson.loads(value)
    if isinstance(value, dict) and all(key.isdigit() for key in val):
        return {int(k): v for k, v in val.items()}
    return val


async def db_init(connection: asyncpg.Connection) -> None:
    await connection.set_type_codec("jsonb", schema="pg_catalog", encoder=_encode_jsonb, decoder=_decode_jsonb)

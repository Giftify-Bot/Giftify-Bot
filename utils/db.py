from __future__ import annotations

import json
from typing import Any

import asyncpg

__all__ = ("db_init",)


def _encode_jsonb(value: Any) -> str:
    return json.dumps(value)


def _decode_jsonb(value: str) -> Any:
    return json.loads(value)


async def db_init(connection: asyncpg.Connection) -> None:
    await connection.set_type_codec(
        "jsonb", schema="pg_catalog", encoder=_encode_jsonb, decoder=_decode_jsonb
    )

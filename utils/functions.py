from typing import Dict, List, Literal, Optional, Sequence, TypeVar, overload

from discord import Member, Object

T = TypeVar("T")
V = TypeVar("V")


class MemberProxy(Object):
    def __init__(self, id: int) -> None:
        self.id = id
        super().__init__(id=id, type=Member)

    @property
    def mention(self) -> str:
        return f"<@{self.id}>"


def safe_format(message: str, **kwargs) -> str:
    """A poorly written format function."""
    for key, value in kwargs.items():
        formatted_key = "{" + key + "}"
        message = message.replace(formatted_key, str(value))
    return message


def bold(message: str) -> str:
    return f"**{message}**"


@overload
def filter_none(obj: Sequence[Optional[T]]) -> List[T]:
    pass


@overload
def filter_none(obj: Dict[T, V], filter_keys: Literal[True]) -> Dict[T, V]:
    pass


def filter_none(obj, filter_keys: bool = False):
    if isinstance(obj, list):
        return [item for item in obj if item is not None]
    elif isinstance(obj, dict):
        if filter_keys:
            return {key: value for key, value in obj.items() if key is not None}
        else:
            return {key: value for key, value in obj.items() if value is not None}
    else:
        return obj

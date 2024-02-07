from typing import Tuple

from discord import app_commands

__all__: Tuple[str, ...] = (
    "TransformerError",
    "MaxChannelConfigCreationError",
    "GiveawayError",
    "ButtonOnCooldown",
    "InvalidRolesPassed",
    "InvalidMentionablesPassed",
    "InvalidTime",
    "InvalidAmount",
    "InvalidColor",
    "InvalidMessage",
    "InvalidRaffle",
    "InvalidEmoji",
    "InvalidChannelPassed",
    "InvalidDonationCategoryError",
    "DonationError",
    "DonationPermissionsError",
    "DonationCategoryError",
    "RaffleError",
)


class TransformerError(app_commands.TransformerError):
    """Custom Exception raised when transforming"""

    def __init__(self, message: str) -> None:
        self.message = message


class MaxChannelConfigCreationError(Exception):
    """Error raised if user tries to edit config for more than 5 channels."""


class GiveawayError(Exception):
    """Error raised in a giveaway."""


class ButtonOnCooldown(Exception):
    def __init__(self, retry_after: float):
        self.retry_after = retry_after


class InvalidRolesPassed(TransformerError):
    pass


class InvalidMentionablesPassed(TransformerError):
    pass


class InvalidTime(TransformerError):
    pass


class InvalidAmount(TransformerError):
    pass


class InvalidColor(TransformerError):
    pass


class InvalidMessage(TransformerError):
    pass


class InvalidRaffle(TransformerError):
    pass


class InvalidEmoji(TransformerError):
    pass


class InvalidChannelPassed(TransformerError):
    pass


class InvalidDonationCategoryError(TransformerError):
    pass


class DonationError(Exception):
    pass


class DonationPermissionsError(app_commands.CheckFailure):
    def __init__(self, message: str) -> None:
        self.message = message


class DonationCategoryError(app_commands.CheckFailure):
    def __init__(self, message: str) -> None:
        self.message = message


class RaffleError(Exception):
    pass

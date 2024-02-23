from typing import Tuple

from discord import app_commands

__all__: Tuple[str, ...] = (
    "TransformerError",
    "MaxChannelConfigCreationError",
    "GiveawayError",
    "ButtonOnCooldownError",
    "InvalidRolesPassedError",
    "InvalidMentionablesPassedError",
    "InvalidTimeError",
    "InvalidAmountError",
    "InvalidColorError",
    "InvalidMessageError",
    "InvalidRaffleError",
    "InvalidEmojiError",
    "InvalidChannelPassedError",
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


class ButtonOnCooldownError(Exception):
    def __init__(self, retry_after: float) -> None:
        self.retry_after = retry_after


class InvalidRolesPassedError(TransformerError):
    pass


class InvalidMentionablesPassedError(TransformerError):
    pass


class InvalidTimeError(TransformerError):
    pass


class InvalidAmountError(TransformerError):
    pass


class InvalidColorError(TransformerError):
    pass


class InvalidMessageError(TransformerError):
    pass


class InvalidRaffleError(TransformerError):
    pass


class InvalidEmojiError(TransformerError):
    pass


class InvalidChannelPassedError(TransformerError):
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

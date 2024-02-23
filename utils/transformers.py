import datetime
import re
from typing import Dict, List, Tuple, Union

import discord
import emoji
from discord import app_commands
from discord.ext import commands

from core.tree import Interaction
from models.donation_settings import GuildDonationConfig
from models.raffles import Raffle
from utils.exceptions import (
    InvalidAmountError,
    InvalidChannelPassedError,
    InvalidColorError,
    InvalidDonationCategoryError,
    InvalidEmojiError,
    InvalidMentionablesPassedError,
    InvalidMessageError,
    InvalidRaffleError,
    InvalidRolesPassedError,
    InvalidTimeError,
)

TIME_REGEX = re.compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([smhd])")
TIME_DICT = {"s": 1, "m": 60, "h": 3600, "d": 86400}

AMOUNT_REGEX = re.compile(r"(\d{1,15}(?:[.,]?\d{1,15})?)([kmbt]?)")
AMOUNT_DICT = {"k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12}


__all___: Tuple[str, ...] = (
    "RolesTransformer",
    "BonusRolesTransformer",
    "TextChannelsTransformer",
    "TimeTransformer",
    "AmountTransformer",
    "EmojiTransformer",
    "ColourTransformer",
    "MessageTransformer",
    "DonationCategoryTransformer",
)


class RolesTransformer(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str) -> List[discord.Role]:
        roles_string = value.split()
        roles: List[discord.Role] = []

        ctx = await commands.Context.from_interaction(interaction)

        for role_string in roles_string:
            try:
                role = await commands.RoleConverter().convert(ctx, role_string.strip())
            except commands.RoleNotFound:
                raise InvalidRolesPassedError(f"{role_string!r} is not a valid role.")

            else:
                if role_string == "@everyone":
                    raise InvalidRolesPassedError(f"{role_string!r} is not a valid role.")
                roles.append(role)

        return roles[:5]


class MentionablesTransformer(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str) -> List[Union[discord.Member, discord.Role]]:
        mentionables: List[Union[discord.Member, discord.Role]] = []

        ctx = await commands.Context.from_interaction(interaction)

        for mentionable_string in value.split():
            # Better way is to use commands.run_converters but we can't use it here.
            try:
                mentionable = await commands.RoleConverter().convert(ctx, mentionable_string.strip())
            except commands.RoleNotFound:
                pass
            else:
                if mentionable_string == "@everyone":
                    raise InvalidRolesPassedError(f"{mentionable_string!r} is not a valid member or role.")
                mentionables.append(mentionable)
                continue

            try:
                mentionable = await commands.MemberConverter().convert(ctx, mentionable_string.strip())
            except commands.MemberNotFound:
                raise InvalidMentionablesPassedError(f"{mentionable_string!r} is not a valid member or role.")

            mentionables.append(mentionable)

        return mentionables


class BonusRolesTransformer(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str) -> Dict[discord.Role, int]:
        roles_string = value.split()
        roles: Dict[discord.Role, int] = {}

        ctx = await commands.Context.from_interaction(interaction)

        for multiplier_roles_role_string in roles_string:
            if ":" not in multiplier_roles_role_string:
                raise InvalidRolesPassedError("You must use `:` to split the role and bonus entries.")
            try:
                (
                    role_string,
                    multiplier_roles_entries,
                ) = multiplier_roles_role_string.split(":")
            except ValueError:
                raise InvalidRolesPassedError("Too many `:` found, expected only 1.")
            try:
                role = await commands.RoleConverter().convert(ctx, role_string.strip())
            except commands.RoleNotFound:
                raise InvalidRolesPassedError(f"{role_string!r} is not a valid role.")
            try:
                multiplier_roles_entries = int(multiplier_roles_entries)
            except ValueError:
                raise InvalidRolesPassedError(
                    f"{multiplier_roles_entries!r} is not a valid number of bonus entries for {role_string}"
                )

            if multiplier_roles_entries > 5:
                raise InvalidRolesPassedError("A role cannot have more than 5 bonus entries.")
            else:
                if role_string == "@everyone":
                    raise InvalidRolesPassedError(f"{role_string!r} is not a valid role.")
                roles[role] = multiplier_roles_entries

        return roles


class TextChannelsTransformer(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str) -> List[discord.TextChannel]:
        channels_string = value.split()
        channels: List[discord.TextChannel] = []

        ctx = await commands.Context.from_interaction(interaction)

        for channel_string in channels_string:
            try:
                role = await commands.TextChannelConverter().convert(ctx, channel_string.strip())
            except commands.RoleNotFound:
                raise InvalidChannelPassedError(f"{channel_string!r} is not a valid channel.")

            else:
                channels.append(role)

        return channels[:5]


class TimeTransformer(app_commands.Transformer):
    async def transform(self, interaction: Interaction, argument: str) -> datetime.datetime:
        matches = TIME_REGEX.findall(argument.lower())
        delta = datetime.timedelta()

        for value, unit in matches:
            try:
                seconds = TIME_DICT[unit] * float(value)
                delta += datetime.timedelta(seconds=seconds)
            except KeyError:
                raise InvalidTimeError(
                    (
                        f"Invalid time unit {unit!r}. "
                        f"Please provide a valid time unit such as 'h' for hours, 'm' for minutes, 's' for seconds, or 'd' for days. "
                        f"Examples of valid input include: 12h, 15h2m, 1d, etc."
                    ),
                )
            except ValueError:
                raise InvalidTimeError(
                    f"Invalid value {value!r} provided. Please provide a valid number.",
                )

        if delta.total_seconds() < 10 or delta.total_seconds() > 1209600:  # 10 seconds and 2 weeks in seconds
            raise InvalidTimeError(
                "The time duration must be greater than 10 seconds and less than 2 weeks.",
            )

        current_time = datetime.datetime.now(datetime.timezone.utc)

        return current_time + delta


class AmountTransformer(app_commands.Transformer):
    async def transform(self, interaction: Interaction, argument: str) -> int:
        match = AMOUNT_REGEX.match(argument.lower())
        if match:
            value = float(match.group(1).replace(",", ""))
            suffix = match.group(2)
            multiplier_roles = AMOUNT_DICT.get(suffix, 1)
            result = int(value * multiplier_roles)
            if result > 100_000_000_000_000:
                raise InvalidAmountError("Invalid amount. The number is too big.")
            return result
        elif argument.isdigit():
            result = int(argument)
            if result > 100_000_000_000_000:
                raise InvalidAmountError("Invalid amount. The number is too big.")
            return result
        else:
            try:
                result = int(float(argument))
                if result > 100_000_000_000_000:
                    raise InvalidAmountError("Invalid amount. The number is too big.")
                return result
            except ValueError:
                raise InvalidAmountError("Invalid amount format. Please provide a valid numerical value.")


class EmojiTransformer(app_commands.Transformer):
    async def transform(self, interaction: Interaction, argument: str) -> str:
        if argument in emoji.UNICODE_EMOJI_ENGLISH:
            return argument

        emote = discord.PartialEmoji.from_str(argument)
        if not emote.id:
            raise InvalidEmojiError(f"{argument!r} is not a valid emoji.")

        return str(emote)


class ColourTransformer(app_commands.Transformer):
    async def transform(self, interaction: Interaction, argument: str) -> int:
        try:
            color = discord.Colour.from_str(argument)
            return int(color)
        except ValueError:
            raise InvalidColorError(
                "The given colour is not a valid hexadecimal value.",
            )


class MessageTransformer(app_commands.Transformer):
    async def transform(self, interaction: Interaction, argument: str) -> discord.PartialMessage:
        ctx = await commands.Context.from_interaction(interaction)

        try:
            message = await commands.PartialMessageConverter().convert(ctx, argument)
        except commands.BadArgument as error:
            raise InvalidMessageError(str(error))
        else:
            if message.guild is None:
                raise InvalidMessageError("The message must belong to a server, not private channels.")
            else:
                return message


class DonationCategoryTransformer(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str) -> GuildDonationConfig:
        assert interaction.guild is not None

        config = interaction.client.get_donation_config(interaction.guild, value)
        if not config:
            raise InvalidDonationCategoryError(
                f"The donation category of name {value} does not exist!",
            )

        return config

    async def autocomplete(
        self,
        interaction: Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        assert interaction.guild is not None

        return [
            app_commands.Choice(name=category, value=category)
            for category in interaction.client.get_guild_donation_categories(interaction.guild)
            if current.lower() in category.lower()
        ]


class RaffleTransformer(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: str) -> Raffle:
        assert interaction.guild is not None

        raffle = await interaction.client.fetch_raffle(interaction.guild, value)
        if not raffle:
            raise InvalidRaffleError(
                f"The raffle of name {value} does not exist!",
            )

        return raffle

    async def autocomplete(
        self,
        interaction: Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        assert interaction.guild is not None

        return [
            app_commands.Choice(name=raffle.name, value=raffle.name)
            for raffle in await interaction.client.fetch_raffles(interaction.guild)
            if current.lower() in raffle.name.lower()
        ]

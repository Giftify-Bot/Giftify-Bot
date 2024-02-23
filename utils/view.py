import contextlib
from typing import TYPE_CHECKING, List, NamedTuple, Optional, Union

import discord
import sentry_sdk
from discord.ext import commands

from core.tree import Interaction
from utils.constants import (
    GIVEAWAY_EMOJI,
    PARTICIPANTS_EMOJI,
    SUCCESS_EMOJI,
    WARN_EMOJI,
)
from utils.exceptions import ButtonOnCooldownError, GiveawayError
from utils.paginator import BaseButtonPaginator

if TYPE_CHECKING:
    from models.giveaways import Giveaway


class Participant(NamedTuple):
    user_id: int
    entries: int


class BaseView(discord.ui.View):
    children: List[Union[discord.ui.Button, discord.ui.Select]]
    message: Optional[Union[discord.Message, discord.InteractionMessage]] = None
    author: Optional[Union[discord.Member, discord.User]] = None

    async def on_error(self, interaction: Interaction, error: Exception, item: discord.ui.Item) -> None:
        if isinstance(error, GiveawayError):
            embed = discord.Embed(
                title="An error was raised while executing this command!",
                description=f"{WARN_EMOJI} {str(error)}",
                color=discord.Colour.red(),
            )
            view = discord.ui.View()
            button = discord.ui.Button(label="Support", url="https://discord.gg/GQSGChbEKz")
            view.add_item(button)

            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        elif isinstance(error, ButtonOnCooldownError):
            embed = discord.Embed(
                title="Stop clicking the button too fast!",
                description=f"{WARN_EMOJI} You are clicking the button too fast. Please retry after {error.retry_after: .2f}s.",
                color=discord.Colour.red(),
            )
            view = discord.ui.View()
            button = discord.ui.Button(label="Support", url="https://discord.gg/GQSGChbEKz")
            view.add_item(button)

            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            if not isinstance(error, (discord.HTTPException, discord.errors.InteractionResponded)):
                if not interaction.response.is_done():
                    await interaction.response.defer(thinking=True, ephemeral=True)

                embed = discord.Embed(
                    title="An error was raised while executing this command!",
                    description=f"{WARN_EMOJI} An unknown error occurred, my developers have been notified about this error.",
                    color=discord.Colour.red(),
                )
                view = discord.ui.View()
                button = discord.ui.Button(label="Support", url="https://discord.gg/GQSGChbEKz")
                view.add_item(button)

                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                sentry_sdk.capture_exception(error)
                return interaction.client.log_handler.log.exception("Exception occurred in the View:\n", exc_info=error)

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                item.disabled = True

        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


class LeaveGiveawayView(BaseView):
    def __init__(
        self,
        interaction: Interaction,
        giveaway: "Giveaway",
        button: "GiveawayButton",
    ):
        self.interaction = interaction
        self.giveaway = giveaway
        self.button = button
        super().__init__(timeout=60)

    @discord.ui.button(label="Leave Giveaway", style=discord.ButtonStyle.red)
    async def callback(self, interaction: Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()

        assert interaction.message is not None
        assert isinstance(interaction.user, discord.Member)

        entries = await self.giveaway.leave(interaction.user)

        self.button.label = str(entries)
        await self.interaction.edit_original_response(view=self.button.view)

        embed = discord.Embed(
            colour=discord.Colour.green(),
            description=f"> {SUCCESS_EMOJI} You have successfully left the giveaway!",
        )

        await interaction.edit_original_response(
            embed=embed,
            view=None,
        )


class GiveawayButton(discord.ui.Button["GiveawayView"]):
    def __init__(
        self,
        reaction: str,
        style: discord.ButtonStyle,
        participant_count: Optional[int],
        disabled: bool = False,
    ):
        super().__init__(
            label=str(participant_count or "0"),
            emoji=reaction,
            style=style,
            custom_id="JOIN_GIVEAWAY_BUTTON",
            disabled=disabled,
        )

    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.defer()

        assert interaction.message is not None
        assert interaction.guild is not None
        assert interaction.channel is not None
        assert isinstance(interaction.user, discord.Member)

        giveaway = await interaction.client.fetch_giveaway(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            message_id=interaction.message.id,
        )
        if giveaway is None:
            raise GiveawayError("The giveaway associated with this message was not found.")

        try:
            entries = await giveaway.join(interaction.user)
        except GiveawayError as error:
            return await interaction.client.send(
                interaction=interaction,
                message=str(error),
                reason="warn",
                ephemeral=True,
                view=LeaveGiveawayView(interaction, giveaway, self)
                if "You have already joined the giveaway." in str(error)
                else BaseView(),  # I don't know why cant we pass None to this.
            )
        else:
            self.label = str(entries)
            await interaction.edit_original_response(view=self.view)

        await interaction.client.send(interaction, "You have successfully joined the giveaway!", ephemeral=True)


class ParticipantsPaginator(BaseButtonPaginator[Participant]):
    async def format_page(self, participants: List[Participant], /) -> discord.Embed:
        assert self.bot is not None

        description = "These are the members that have participated in the giveaway:\n\n"

        start_number = (self.current_page - 1) * self.per_page

        for i, (user_id, user_entries) in enumerate(participants):
            verb = "entry" if user_entries == 1 else "entries"

            display_number = start_number + i + 1
            description += f"{display_number}. <@!{user_id}> (**{user_entries}** {verb})\n"

        total_participants: int = self.extras.get("total_participants", 0) if self.extras is not None else 0
        total_unique_participants: int = self.extras.get("total_unique_participants", 0) if self.extras is not None else 0

        description += f"\nTotal Entries: **{total_participants} ({total_unique_participants} Participants)**"
        embed = discord.Embed(description=description, colour=self.bot.colour)
        embed.set_author(name="Giveaway Participants", url=self.bot.user.display_avatar)

        embed.set_footer(text=f"Page {self.current_page}/{self.total_pages}")

        return embed


class ParticipantsButton(discord.ui.Button["GiveawayView"]):
    def __init__(self, reaction: str):
        super().__init__(
            label="Participants",
            emoji=reaction,
            custom_id="PARTICIPANTS_BUTTON",
        )

    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        assert interaction.message is not None
        assert interaction.guild is not None
        assert interaction.channel is not None

        giveaway = await interaction.client.fetch_giveaway(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            message_id=interaction.message.id,
        )
        if giveaway is None:
            raise GiveawayError("The giveaway associated with this message was not found.")
        if giveaway.participants:
            unqiue_entries = set(giveaway.participants)
            entries = [
                Participant(user_id=user_id, entries=giveaway.participants.count(user_id)) for user_id in unqiue_entries
            ]

            view = ParticipantsPaginator(
                entries=entries,
                per_page=10,
                target=interaction,
                extras={
                    "total_participants": len(entries),
                    "total_unique_participants": len(unqiue_entries),
                },
            )
            embed = await view.embed()
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.client.send(
                interaction,
                "No one has participated in this giveaway yet.",
                reason="warn",
                ephemeral=True,
            )


class GiveawayView(BaseView):
    def __init__(
        self,
        reaction: str = GIVEAWAY_EMOJI,
        participants_reaction: str = PARTICIPANTS_EMOJI,
        button_style: discord.ButtonStyle = discord.ButtonStyle.blurple,
        *,
        participant_count: Optional[int] = None,
        disabled: bool = False,
    ):
        super().__init__(timeout=None)

        self.add_item(
            GiveawayButton(
                reaction,
                button_style,
                participant_count=participant_count,
                disabled=disabled,
            )
        )
        self.add_item(ParticipantsButton(reaction=participants_reaction))

        def key(interaction: Interaction):
            return interaction.user.id

        self.cooldown = commands.CooldownMapping.from_cooldown(3, 5, key)

    async def interaction_check(self, interaction: Interaction):
        if retry_after := self.cooldown.update_rate_limit(interaction):
            raise ButtonOnCooldownError(retry_after)

        return await super().interaction_check(interaction)


class MainView(BaseView):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Invite", url="https://giftifybot.vercel.app/invite"))
        self.add_item(discord.ui.Button(label="Support Server", url="https://giftifybot.vercel.app/support"))
        self.add_item(discord.ui.Button(label="Documentation", url="https://giftifybot.vercel.app/documentation"))
        self.add_item(discord.ui.Button(label="Website", url="https://giftifybot.vercel.app/"))


class ConfirmationView(BaseView):
    def __init__(
        self,
        *,
        timeout: float,
        interaction: Interaction,
        success_message: str,
        cancel_message: str,
    ) -> None:
        super().__init__(timeout=timeout)
        self.interaction = interaction
        self.success_message = success_message
        self.cancel_message = cancel_message
        self.value: Optional[bool] = None

    @property
    def success_embed(self) -> discord.Embed:
        return discord.Embed(
            description=f"{SUCCESS_EMOJI} {self.success_message}",
            colour=discord.Colour.green(),
        )

    @property
    def cancel_embed(self) -> discord.Embed:
        return discord.Embed(
            description=f"{SUCCESS_EMOJI} {self.cancel_message}",
            colour=discord.Colour.green(),
        )

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user and interaction.user.id == self.interaction.user.id:
            return True
        else:
            await interaction.response.send_message("This confirmation dialog is not for you.", ephemeral=True)
            return False

    async def on_timeout(self) -> None:
        with contextlib.suppress(discord.HTTPException):
            for item in self.children:
                item.disabled = True
            await self.interaction.edit_original_response(view=self)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: Interaction, button: discord.ui.Button):
        self.value = True
        await interaction.response.edit_message(embed=self.success_embed, view=None)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: Interaction, button: discord.ui.Button):
        self.value = False
        await interaction.response.edit_message(embed=self.cancel_embed, view=None)

        self.stop()

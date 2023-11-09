from discord import app_commands

from bot import Giftify

from .raffle import RaffleBase
from .raffle_deputy import RaffleDeputy
from .raffle_tickets import RaffleTickets


@app_commands.guild_only()
class Raffles(
    RaffleBase,
    RaffleDeputy,
    RaffleTickets,
    name="raffle",
):
    """Start and manage raffles."""

    def __init__(self, bot: Giftify) -> None:
        self.bot = bot
        super().__init__()


async def setup(bot: Giftify) -> None:
    await bot.add_cog(Raffles(bot))

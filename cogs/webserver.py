import logging
import os

import aiohttp
from aiohttp import web
from discord.ext import commands, tasks

from bot import Giftify

log = logging.getLogger("cogs.webserver")


class WebServer(commands.Cog):
    def __init__(self, bot: Giftify):
        self.bot = bot
        self.app = web.Application()
        self.app.router.add_get("/", self.handle)
        self.app.router.add_post("/guilds", self.handle_guilds)

        self.update_stats.start()

    async def cog_load(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        self.site = web.TCPSite(runner, "0.0.0.0", 8080)
        await self.site.start()
        log.info("Webserver started on port 8080.")

    async def cog_unload(self):
        self.update_stats.stop()
        await self.site.stop()

    async def handle(self, request: web.Request):
        return web.json_response({"success": 200})

    async def handle_guilds(self, request: web.Request):
        if request.headers.get("Authorization") != os.environ["WEBSERVER_AUTH"]:
            return web.json_response({"error": "401: Unauthorized"}, status=401)

        guilds = [
            {
                "id": guild.id,
                "name": guild.name,
                "icon": guild.icon,
                "member_count": guild.member_count,
            }
            for guild in self.bot.guilds
        ]

        return web.json_response({"success": True, "guilds": guilds})

    @tasks.loop(minutes=30)
    async def update_stats(self):
        token = os.environ.get("DBL_TOKEN")
        if token is None:
            return

        headers = {"Authorization": token, "Content-Type": "application/json"}
        payload = {
            "server_count": len(self.bot.guilds),
            "shard_count": self.bot.shard_count,
        }

        try:
            async with self.bot.session.post(
                f"https://top.gg/api/bots/stats",
                json=payload,
                headers=headers,
            ) as resp:
                if resp.status == 200:
                    log.info(f"Server count updated to {payload['server_count']} on Top.gg")
                else:
                    log.error(f"Failed to update server count. Status code: {resp.status}")
        except aiohttp.ClientError as error:
            log.error(f"Error updating server count: {error}")


async def setup(bot: Giftify) -> None:
    await bot.add_cog(WebServer(bot))

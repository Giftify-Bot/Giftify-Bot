import datetime
import logging
import os
from typing import Optional

import discord
from aiohttp import web
from discord.ext import commands

from bot import Giftify

log = logging.getLogger("cogs.webserver")


class WebServer(commands.Cog):
    def __init__(self, bot: Giftify):
        self.bot = bot
        self.app = web.Application()
        self.app.router.add_get("/", self.handle)
        self.app.router.add_post("/guilds", self.handle_guilds)

    async def cog_load(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        self.site = web.TCPSite(runner, "0.0.0.0", 8080)
        await self.site.start()
        log.info("Webserver started on port 8080.")

    async def cog_unload(self):
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


async def setup(bot: Giftify) -> None:
    await bot.add_cog(WebServer(bot))

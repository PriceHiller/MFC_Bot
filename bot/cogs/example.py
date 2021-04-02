from bot import Bot

from bot.cogs import BaseCog
from bot.cogs import command


class Ping(BaseCog):

    @command.command()
    async def ping(self, ctx):
        await ctx.send("pong")

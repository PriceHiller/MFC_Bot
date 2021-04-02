from Bot import Bot

from Bot.Cogs import BaseCog
from Bot.Cogs import command


class Ping(BaseCog):

    @command.command()
    async def ping(self, ctx):
        await ctx.send("pong")

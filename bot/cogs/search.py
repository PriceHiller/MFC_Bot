from bot.cogs import BaseCog
from bot.cogs import command


class Search(BaseCog):

    @command.group(name="search")
    async def search(self, ctx: command.Context, *message: str):
        """Returns a valid search string through a web engine, default is google unless specified"""
        if not ctx.invoked_subcommand:
            return await self.google(ctx, *message)

    @search.command(aliases=["g"])
    async def google(self, ctx, *message: str):
        """Returns a google search with search query, aliases: g"""
        message = "+".join(message)
        await ctx.send(f"https://www.google.com/search?q={message}")

    @search.command(aliases=["b"])
    async def bing(self, ctx, *message: str):
        """Returns a bing search with search query, aliases: b"""
        message = "+".join(message)
        await ctx.send(f"https://www.bing.com/search?q={message}")

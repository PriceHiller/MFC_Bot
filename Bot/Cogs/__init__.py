import importlib
import pkgutil
import json

import logging

from Bot import Bot

from discord.ext import commands
from discord.ext.commands import Cog


log = logging.getLogger(__name__)


class BaseCog(commands.Cog):

    def __init__(self, bot: Bot):
        self.bot = bot

    @staticmethod
    def find_subclasses(package: str = "Bot.Cogs", recursive: bool = True) -> None:
        """ Import all submodules of a module, recursively, including subpackages

        Credit to: https://stackoverflow.com/a/25562415/13079078, Mr. B on stackoverflow

        :param recursive: bool
        :param package: package (name or actual module)
        :type package: str | module
        """
        if isinstance(package, str):
            package = importlib.import_module(package)
        for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
            full_name = package.__name__ + '.' + name
            importlib.import_module(full_name)
            if recursive and is_pkg:
                BaseCog.find_subclasses(full_name, recursive)

    @staticmethod
    def load_cogs(bot: Bot) -> None:
        for subclass in BaseCog.__subclasses__():
            bot.add_cog(subclass(bot))
            log.info(f"Loaded cog: {subclass.__name__} ({subclass.__module__})")


command = commands
listener = Cog.listener

__all__ = [
    "BaseCog",
    "command",
    "listener"
]

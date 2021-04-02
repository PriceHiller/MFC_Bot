import logging
import os

import yaml

from logging import config
from pathlib import Path

from discord.ext.commands import AutoShardedBot
from discord.ext.commands import Context
from discord import Intents

root_path = Path(__file__).parent
log = logging.getLogger(__name__)


class Bot(AutoShardedBot):

    def __init__(self,
                 command_prefix: str = "!",
                 **options):

        super().__init__(command_prefix, **options)

    async def on_command(self, ctx: Context):
        """
        Override the on_command function to log all command usages through the Bot
        """

        try:
            log.info(f'{ctx.author} ({ctx.author.id}) invoked a command '
                     f'\"{ctx.message.content}\" in the guild {ctx.guild} ({ctx.guild.id}) '
                     f'in channel {ctx.channel.name} ({ctx.channel.id})')
        except AttributeError:
            log.info(f'{ctx.author} ({ctx.author.id}) invoked a command '
                     f'\"{ctx.message.content}\" in DMs ({ctx.channel.id})')

    async def on_ready(self):
        log.info(f"Logged in as {self.user} ({self.user.id})")
        log.info(f"Have access to the following guilds: "
                 f"{', '.join([str(guild.name) + ' (' + str(guild.id) + ')' for guild in self.guilds])}")


def setup_logging() -> None:
    try:
        if log_config_path := os.getenv("log_config_path", default=None):
            log_config_path = Path(log_config_path)
        else:
            log_config_path = root_path / "log_config.yaml"

        with open(log_config_path) as f:
            log_config = yaml.safe_load(f)
    except FileNotFoundError as error:
        print(f"Could not find your log config at: {str(error).split(' ')[-1]}")
        return

    config.dictConfig(log_config)


def dynamic_env_parse(instance_vars, base_match: str, object):
    def convert_var(input_var):
        if str(input_var).isnumeric():
            return int(input_var)
        elif str(input_var).casefold() == "false":
            return False
        elif str(input_var).casefold() == "true":
            return True
        else:
            return str(input_var)

    for var in list(instance_vars.keys()):
        if env_var := os.getenv(base_match + var, default=None):

            if "[" in str(env_var)[0] and "]" in str(env_var)[-1]:
                instance_vars[var] = \
                    [convert_var(split_var) for split_var in str(env_var).strip("[").strip("]").split(",")]
            else:
                instance_vars[var] = convert_var(env_var)

            try:
                object(**instance_vars)
            except TypeError as error:
                error_attr = str(error).split(" ")[-1].strip("'")
                instance_vars.pop(error_attr)

    return instance_vars


bot = Bot(intents=Intents.all())

__all__ = [
    "bot",
    "dynamic_env_parse",
    "setup_logging",
    "Bot"
]

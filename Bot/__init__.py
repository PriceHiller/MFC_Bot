import logging
import os

import yaml
import aiofiles

from logging import config
from pathlib import Path
from urllib import parse

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectionError

from discord import Embed
from discord import Color
from discord.ext import commands
from discord.ext.commands import AutoShardedBot
from discord.ext.commands import Context
from discord import Intents

from dotenv import load_dotenv

from Bot.Config.config import Config

root_path = Path(__file__).parent
log = logging.getLogger(__name__)

environment_path = root_path.parent / ".env"

config_path = root_path.parent / "config.json"

bot_config = Config(config_path)

if environment_path.exists():
    load_dotenv(environment_path)
else:
    log.warning("A .env file is not defined in the Bot directory, "
                "ensure your variables are exported in the environment")


class Bot(AutoShardedBot):

    def __init__(self,
                 command_prefix: str = (bot_config.prefix or "-"),
                 **options):
        super().__init__(command_prefix, **options)

    @staticmethod
    async def write(path, data: str):
        async with aiofiles.open(path, "w+", encoding="UTF-8") as f:
            await f.write(data)

    @staticmethod
    async def read(path) -> str:
        async with aiofiles.open(path, encoding="UTF-8") as f:
            return await f.read()

    def default_embed(self, **embed_kwargs):
        class DefaultEmbed(Embed):

            def __init__(self, **kwargs):
                color_rgb = bot_config.config_dict["Embed-Color"]
                super().__init__(color=Color.from_rgb(r=color_rgb["r"], g=color_rgb["g"], b=color_rgb["b"]),
                                 **kwargs)

        embed = DefaultEmbed(**embed_kwargs)

        embed.set_author(name=self.user.display_name,
                         url=os.getenv("API_URL", default="https://www.discord.com"),
                         icon_url=self.user.avatar_url)
        embed.set_thumbnail(url=self.user.avatar_url)
        embed.set_footer(text=f"Written by Sbinalla (Price Hiller)", icon_url=self.user.avatar_url)
        return embed

    async def on_command_error(self, ctx: commands.Context, exception: commands.errors.CommandInvokeError):
        error = getattr(exception, "original", exception)
        if isinstance(error, commands.errors.CheckFailure):
            log.debug(f"Check function checking command {ctx.command} failed")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            log.debug(f"Argument was missing for {ctx.command}, {exception}")
            split_exception = str(exception).split(" ")
            await ctx.send("`" + split_exception[0] + "` " + " ".join(split_exception[1:]).strip(".")
                           + f" for the command: `{ctx.command}`. See `{ctx.prefix}help {ctx.command}`.")
        elif isinstance(error, commands.errors.MemberNotFound):
            exception = str(exception).replace('"', '`')
            await ctx.send(f"{exception}")
        elif isinstance(error, commands.errors.CommandNotFound):
            exception = str(exception).replace('"', '`')
            await ctx.send(f"{exception}\n"
                           f"Please see `{self.command_prefix}help`")
        elif isinstance(error, commands.errors.RoleNotFound):
            await ctx.send(f"{exception}\n"
                           f"Perhaps you are in the wrong server?")
        else:
            try:
                raise exception
            except Exception:
                await ctx.send("`An Error Occurred`")
                log.exception("Re-raised a caught exception for log")

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
        response = await APIRequest.post("/user/verify")
        if response.status == 200:
            log.info(f"Connected and authenticated with the API at: {APIRequest.api_url}")
        else:
            log.warning(f"Could not connect or unauthenticated with the API at: {APIRequest.api_url}, "
                        f"status code: {response.status}")
        log.info(f"Logged in as {self.user} ({self.user.id})")
        log.info(f"Prefix is set to \"{self.command_prefix}\"")
        log.info(f"Have access to the following guilds: "
                 f"{', '.join([str(guild.name) + ' (' + str(guild.id) + ')' for guild in self.guilds])}")


class APIRequest:
    api_url = os.getenv("API_URL").strip("/")
    log.debug(f"API url registered as {api_url}")
    api_token = os.getenv("API_TOKEN")
    headers = {"Authorization": "Bearer " + api_token}

    class Response:

        def __init__(self, json: dict, status: int):
            self.json = json
            self.status = status

    @staticmethod
    def verify_url(url: str, checks=("scheme", "netloc")):
        valid_url = parse.urlparse(url)
        return all([getattr(valid_url, check_attr) for check_attr in checks])

    @classmethod
    async def get(cls, endpoint: str = "/") -> Response:
        full_url = cls.api_url + endpoint
        if not cls.verify_url(full_url):
            return cls.Response({}, 418)
        async with ClientSession(headers=cls.headers) as session:
            try:
                log.debug(f"GET request issued to {full_url}")
                async with session.get(full_url, ssl=False) as get_session:
                    json_dict = await get_session.json() or {}
                    return cls.Response(json_dict, get_session.status)
            except ClientConnectionError as error:
                log.warning(f"Could not connect to the API at url {cls.api_url}, error: {error}")
                return cls.Response({}, 400)
            except UnicodeError:
                log.warning(f"Unicode error thrown due to URL, likely malformed, URL: {full_url}")
                return cls.Response({}, 400)

    @classmethod
    async def post(cls, endpoint: str = "/", data: dict = None) -> Response:
        full_url = cls.api_url + endpoint
        if not cls.verify_url(full_url):
            log.warning(f"URL {full_url} is not a valid url!")
            return cls.Response({}, 400)
        async with ClientSession(headers=cls.headers) as session:
            try:
                log.debug(f"POST request issued to {full_url}")
                async with session.post(full_url, json=data, ssl=False) as post_session:
                    json_dict = await post_session.json() or {}
                    return cls.Response(json_dict, post_session.status)
            except UnicodeError:
                log.warning(f"Unicode error thrown due to URL, likely malformed, URL: {full_url}")
                return cls.Response({}, 400)
            except ClientConnectionError as error:
                log.warning(f"Could not connect to the API at url {cls.api_url}, error: {error}")
                return cls.Response({}, 400)


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
    "Bot",
    "APIRequest"
]

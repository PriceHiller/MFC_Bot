import os
import asyncio
import logging

import uvloop

from dotenv import load_dotenv

from bot import bot
from bot import root_path
from bot import setup_logging
from bot.cogs import BaseCog

log = logging.getLogger(__name__)


def main():
    environment_path = root_path / ".env"
    if not environment_path.exists():
        log.warning("A .env file is not defined in the bot directory, "
                    "ensure your variables are exported in the environment")

    load_dotenv(environment_path)
    setup_logging()

    loop = asyncio.get_event_loop()
    uvloop.install()
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    BaseCog.find_subclasses()
    BaseCog.load_cogs()

    loop.create_task(bot.start(os.environ["discord_bot_token"]))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        log.info("Shutting down")
        loop.create_task(bot.close())
        log.info("Successfully ended")


if __name__ == "__main__":
    main()

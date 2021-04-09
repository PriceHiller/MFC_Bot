import os
import asyncio
import logging

import uvloop

from Bot import bot
from Bot import setup_logging
from Bot.Cogs import BaseCog

log = logging.getLogger(__name__)


def main():
    setup_logging()

    loop = bot.loop
    uvloop.install()
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    BaseCog.find_subclasses()
    BaseCog.load_cogs(bot)

    loop.create_task(bot.start(os.environ["DISCORD_BOT_TOKEN"]))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        log.info("Shutting down")
        loop.create_task(bot.close())
        log.info("Successfully ended")


if __name__ == "__main__":
    main()

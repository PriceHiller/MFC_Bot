import logging

from discord import Member

from bot.cogs import BaseCog
from bot.cogs import listener

log = logging.getLogger(__name__)


class Join(BaseCog):

    @listener()
    async def on_member_join(self, member: Member):
        log.info(f"Member: {member} ({member.id}) joined the guild "
                 f"{member.guild} ({member.guild.id}!")

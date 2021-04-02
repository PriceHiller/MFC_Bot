import logging

from discord import Member

from Bot.Cogs import BaseCog
from Bot.Cogs import listener

log = logging.getLogger(__name__)


class Join(BaseCog):

    @listener()
    async def on_member_join(self, member: Member):
        log.info(f"Member: {member} ({member.id}) joined the guild "
                 f"{member.guild} ({member.guild.id}!")

import logging

import discord

from Bot import bot_config
from Bot.Cogs import BaseCog
from Bot.Cogs import command
from Bot.Config.Permissions import Permissions

log = logging.getLogger(__name__)

bot_config = bot_config.config_dict


class MatchPlanning(BaseCog):

    @command.group()
    async def mfc(self, ctx: command.Context):
        if not ctx.invoked_subcommand:
            if not await Permissions.check_perms(ctx, str(ctx.command)):
                return

    @mfc.group(aliases=["p"])
    async def plan(self, ctx: command.Context):
        """Shit code for a shit person. Needs a MAJOR refactor once everything is good to go."""
        if not ctx.invoked_subcommand:
            if await Permissions.check_perms(ctx, str(ctx.command)):
                await self.post_match_planning()

    async def post_match_planning(self):

        planning_dict = bot_config["MFC-Guild"]["Match-Planning"]
        channel_id = planning_dict["Channel-ID"]
        if channel := self.bot.get_channel(channel_id):
            channel: discord.TextChannel
            guild: discord.Guild = channel.guild
            ping_role: discord.Role = guild.get_role(planning_dict["Ping-Role"])
            if not ping_role:
                log.critical(f"The Ping-Role of [Match-Planning] was invalid!")
                return
            timezone = planning_dict["Timezone"]
            plan_days = planning_dict["Days"]
            output_messages = [await channel.send(ping_role.mention),
                               await channel.send(f"__All times below are in {timezone}__")]
            error = False
            for day in plan_days.keys():
                emojis = []
                signup_message = day + ": "
                for time, emoji in plan_days[day].items():
                    if not emoji:
                        log.critical(f"The emoji id: {emoji} for [Match-Planning][{day}][{time}] is invalid. "
                                     f"It was not found.")
                        error = True
                        break

                    if emoji in emojis:
                        log.critical(f"The emoji: {emoji} for [Match-Planning][{day}][{time}] is invalid. "
                                     f"It is a duplicate.")
                        error = True
                        break
                    emojis.append(emoji)
                    signup_message += f"{emoji} for {time}"
                if error:
                    for message in output_messages:
                        await message.delete()
                    await channel.send(f"`A config error occurred in Match-Planning.`")
                    return

                message = await channel.send(signup_message)
                for emoji in emojis:
                    await message.add_reaction(emoji)
                output_messages.append(message)
        else:
            log.critical(f"The Channel-ID for Match-Planning is invalid!")

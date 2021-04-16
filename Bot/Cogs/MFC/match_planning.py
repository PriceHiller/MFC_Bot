import logging
import asyncio
import csv
import os

from datetime import datetime
from datetime import timezone
from pathlib import Path

import discord
from discord.ext import tasks

from Bot import Bot
from Bot import bot_config
from Bot import APIRequest
from Bot.Cogs import BaseCog
from Bot.Cogs import command
from Bot.Config.Permissions import Permissions

log = logging.getLogger(__name__)


class MatchPlanning(BaseCog):
    planning_posted = bot_config.config_dict["MFC-Guild"]["Match-Planning"]["Posted"]

    plan_loop_name = "match_plan_loop"

    def __init__(self, bot: Bot):
        bot.loop.create_task(self.plan_loop(), name=self.plan_loop_name)
        super().__init__(bot)

    @command.group(aliases=["pl"])
    async def plan(self, ctx: command.Context):
        """Posts the match planning sign ups if no subcommand is invoked"""
        if not ctx.invoked_subcommand:
            await self.post_match_planning()

    def cog_unload(self):
        for task in asyncio.all_tasks(self.bot.loop):
            if task.get_name() == self.plan_loop_name:
                task.cancel()

    async def plan_loop(self):
        while True:
            log.debug(f"Checking if planning should be posted.")
            await self.bot.wait_until_ready()
            today = datetime.now(tz=timezone.utc).strftime("%A").casefold()
            if today == bot_config.config_dict["MFC-Guild"]["Match-Planning"]["Post-Day"].casefold():
                if not self.planning_posted:
                    await self.post_match_planning()
                    self.planning_posted = True
                    bot_config.config_dict["MFC-Guild"]["Match-Planning"]["Posted"] = True
                    await bot_config.write(bot_config.config_dict)
            elif self.planning_posted:
                self.planning_posted = False
                bot_config.config_dict["MFC-Guild"]["Match-Planning"]["Posted"] = False
                await bot_config.write(bot_config.config_dict)
            await asyncio.sleep(3600) # Sleep for one hour

    @plan.command()
    @Permissions.is_permitted()
    async def dump(self, ctx: command.Context, delete: bool = True):
        match_planning_dict = bot_config.config_dict["MFC-Guild"]["Match-Planning"]
        guild: discord.Guild = ctx.guild
        if not guild:
            await ctx.send(f"This command must be used in a discord server")
            return
        channel: discord.TextChannel = guild.get_channel(int(match_planning_dict["Channel-ID"]))
        if not channel:
            await ctx.send(f"Could not find the relevant channel to dump team sign ups.")
            return
        react_messages: list[int] = match_planning_dict["Message-IDs"]
        react_messages: list[discord.Message] = [await channel.fetch_message(message) for message in react_messages]
        known_discord_teams = await APIRequest.get("/team/all")
        if known_discord_teams.status != 200:
            log.critical(f"Attempted to connect to the API, could not reach it!")
            await ctx.send("Unable to connect to the API.")
            return
        discord_team_ids = [team.get("discord_id") for team in known_discord_teams.json]
        days: dict = match_planning_dict["Days"]
        react_dict = {}
        message_num = -1
        for message in react_messages:
            message_num += 1
            for reaction in message.reactions:
                reaction: discord.Reaction
                users = await reaction.users().flatten()
                for user in users:
                    for role in user.roles:
                        role: discord.Role
                        for discord_team_id in discord_team_ids:
                            day = list(days.keys())[message_num]
                            if not react_dict.get(day):
                                react_dict[day] = {}
                            if role.id == discord_team_id:
                                inv_map = {v: k for k, v in days[day].items()}
                                if not react_dict[day].get(inv_map[str(reaction.emoji)]):
                                    react_dict[day][inv_map[str(reaction.emoji)]] = []
                                react_dict[day][inv_map[str(reaction.emoji)]].append(role.name)

        def write_csv(react_dict: dict, file_path: Path):
            with open(file_path, "w+") as f:
                headers = ["Times (EST)"] + list(react_dict.keys())
                csv_writer = csv.writer(f, delimiter=',', quotechar='"')
                csv_writer.writerow(headers)
                sign_ups = {}
                for day, times in react_dict.items():
                    for time, teams in times.items():
                        if not sign_ups.get(time):
                            sign_ups[time] = []
                        sign_ups[time].append("\n".join(teams))

                for time, teams in sign_ups.items():
                    row = [time] + teams
                    csv_writer.writerow(row)

        loop = asyncio.get_event_loop()
        file_path = Path("signups.csv")
        await loop.run_in_executor(None, write_csv, react_dict, file_path)

        if delete:
            await ctx.send("This dump will be deleted in 60 seconds.", delete_after=60)
            await ctx.send(file=discord.File(file_path), delete_after=60)
        else:
            await ctx.send(file=discord.File(file_path))
        os.remove(file_path)
        log.info(f"Dumped sign ups for {ctx.author}.")

    async def post_match_planning(self):
        log.info(f"Posting Match Planning")
        planning_dict = bot_config.config_dict["MFC-Guild"]["Match-Planning"]
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
            output_messages = [await channel.send(ping_role.mention + " Sign ups for this week."),
                               await channel.send(f"__All times below are in {timezone}__"), ]
            react_messages = []
            error = False
            for day in plan_days.keys():
                emojis = []
                signup_message = ""
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
                    signup_message += f"{emoji} for {time} "
                if error:
                    for message in output_messages:
                        await message.delete()
                    await channel.send(f"`A config error occurred in Match-Planning.`")
                    return

                message = await channel.send(embed=self.bot.default_embed(title=day, description=signup_message))
                for emoji in emojis:
                    await message.add_reaction(emoji)
                output_messages.append(message)
                react_messages.append(message)

            bot_config.config_dict["MFC-Guild"]["Match-Planning"]["Message-IDs"] = \
                [react_message.id for react_message in react_messages]

            await bot_config.write(bot_config.config_dict)

        else:
            log.critical(f"The Channel-ID for Match-Planning is invalid!")

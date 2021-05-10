import asyncio
import logging

import discord
from discord.ext import tasks

from Bot import APIRequest, bot_config
from Bot.Cogs import BaseCog
from Bot.Cogs import command
from Bot.Cogs import listener
from Bot.Config.Permissions import Permissions

log = logging.getLogger(__name__)


class Team(BaseCog):
    embed_loop_team_json = {}

    def __init__(self, bot):
        bot.loop.create_task(self.embed_teams_loop(), name="embed_team_loop")
        super().__init__(bot)

    @command.group(aliases=["t"])
    async def team(self, ctx: command.Context):
        """A group containing all MFC team related commands"""

    @team.group(aliases=["p"])
    @Permissions.is_permitted()
    async def player(self, ctx: command.Context):
        """A sub  group of team containing player related team commands, must be used in a server"""
        if not ctx.guild:
            await ctx.send(f"This command can only be used within a discord server.")
            return

    @player.command(aliases=["a"])
    @Permissions.is_permitted()
    async def add(self, ctx: command.Context, player: discord.Member, team: discord.Role):
        """Adds a player to a team if they've been registered as a player previously."""
        team_lookup = await APIRequest.get(f"/team/discord-id?discord_id={team.id}")
        if team_lookup.status == 404:
            await ctx.send(f"Could not find a team with discord id: `{team.id}`")
            return
        elif team_lookup.status != 200:
            await ctx.send(f"Unable to receive data from the API, something has gone wrong!")
            return
        team_id = team_lookup.json["id"]
        player_lookup = await APIRequest.get(f"/player/discord-id?discord_id={player.id}")
        if player_lookup.status == 404:
            await ctx.send(f"Could not find the player {player.mention}`")
            return
        elif player_lookup.status != 200:
            await ctx.send(f"Unable to receive data from the API, something has gone wrong!")
            return
        player_id = player_lookup.json["id"]
        add_player = await APIRequest.post(f"/team/add-player-to-team?player_id={player_id}&team_id={team_id}")
        if add_player.status == 403:
            await ctx.send(f"Could not authenticate with the API")
            return
        elif add_player.status != 200:
            await ctx.send(f"Unable to receive data from the API, something has gone wrong!")
            return
        await player.add_roles(team)
        await ctx.send(f"Added {player.mention} to {team.mention}")

    @player.command(aliases=["r"])
    @Permissions.is_permitted()
    async def remove(self, ctx: command.Context, player: discord.Member, team: discord.Role):
        """Removes a player from a team if they've been registered as a player previously."""
        team_lookup = await APIRequest.get(f"/team/discord-id?discord_id={team.id}")
        if team_lookup.status == 404:
            await ctx.send(f"Could not find a team with discord id: `{team.id}`")
            return
        elif team_lookup.status != 200:
            await ctx.send(f"Unable to receive data from the API, something has gone wrong!")
            log.error(f"Unable to retrieve data from the API, status: \"{team_lookup.status}\", "
                      f"json: \"{team_lookup.json}\"")
            return
        player_lookup = await APIRequest.get(f"/player/discord-id?discord_id={player.id}")
        if player_lookup.status == 404:
            await ctx.send(f"Could not find the player {player.mention}`")
            return
        elif player_lookup.status != 200:
            await ctx.send(f"Unable to receive data from the API, something has gone wrong!")
            log.error(f"Unable to retrieve data from the API, status: \"{player_lookup.status}\", "
                      f"json: \"{player_lookup.json}\"")
            return
        team_id = team_lookup.json["id"]
        player_id = player_lookup.json["id"]

        if not player_lookup.json["team_id"] == team_id:
            await ctx.send(f"{player.mention} is not on the team {team.mention}")
            return
        print(player_lookup.json, team_lookup.json)
        add_player = await APIRequest.post(f"/team/remove-player-from-team?player_id={player_id}&team_id={team_id}")
        if add_player.status == 403:
            await ctx.send(f"Could not authenticate with the API")
            return
        elif add_player.status != 200:
            await ctx.send(f"Unable to receive data from the API, something has gone wrong!")
            log.error(f"Unable to retrieve data from the API, status: \"{add_player.status}\", "
                      f"json: \"{add_player.json}\"")
            return
        await player.remove_roles(team)
        await ctx.send(f"Removed {player.mention} from {team.mention}")

    @tasks.loop(seconds=600)
    async def embed_teams_loop(self):
        while True:
            await asyncio.sleep(600)  # sleep for 10 minutes
            text_channel_id = bot_config.config_dict["MFC-Guild"]["Automated-ELO-Output"]["Channel-ID"]
            channel: discord.TextChannel = self.bot.get_channel(int(text_channel_id))
            if not channel or type(channel) is not discord.TextChannel:
                log.error(f"Incorrect channel ID passed for Automated-ELO-Output")
            else:
                await channel.purge()
                await self.embed_teams(channel)

    async def embed_teams(self, channel: discord.TextChannel):
        guild: discord.Guild = channel.guild
        team_lookup = await APIRequest.get(f"/team/all")
        if team_lookup.status != 200:
            log.error((f"Could not list teams, status: \"{team_lookup.status}\", json: \"{team_lookup.json}\""))
            return False
        unsorted_teams: [int, list[str]] = {}
        self.embed_loop_team_json = team_lookup.json
        for team in team_lookup.json:
            team: dict
            discord_id = team["discord_id"]
            role = guild.get_role(int(discord_id))
            if not role:
                role = await guild.fetch_roles()
            if role:
                role: discord.Role
                elo = int(team["elo"])
                if not unsorted_teams.get(elo, None):
                    unsorted_teams[elo] = [role.mention]
                else:
                    unsorted_teams[elo].append(role.mention)
            else:
                log.warning(f"Attempted to get team {team['team_name']}, id: {team['id']}, but they their discord role"
                            f"for id {team['discord_id']} was not found!")

        total_teams = len(team_lookup.json)
        embed = self.bot.default_embed(title="MFC Teams",
                                       description=f"All teams registered in MFC by ELO.\n\n"
                                                   f"Total Teams: `{total_teams}`")
        team_position_field_text = ""
        team_name_field_text = ""
        team_elo_text = ""
        # This will give us all teams by elo in an ascending manner by elo
        for team_count, elo in enumerate(reversed(sorted(unsorted_teams))):
            team_count += 1
            teams = unsorted_teams[elo]
            if len(teams) == 1:
                team_position_field_text += f"{team_count}\n"
                team_name_field_text += str(teams[0]) + "\n"
                team_elo_text += str(elo) + "\n"
            else:
                for team in teams:
                    print(team)
                    team_position_field_text += f"{team_count}T\n"
                    team_name_field_text += str(team) + "\n"
                    team_elo_text += str(elo) + "\n"

        embed.add_field(name="Position", value=team_position_field_text)
        embed.add_field(name="Teams", value=team_name_field_text)
        embed.add_field(name="Elo", value=team_elo_text)

        await channel.send(embed=embed)
        return True

    @team.command(aliases=["l"])
    @Permissions.is_permitted()
    async def list(self, ctx: command.Context):
        """Lists all teams"""
        if ctx.channel is discord.DMChannel:
            await ctx.send(f"This command must be invoked in a discord server!")
            return f"This command must be invoked in a discord server!"

        content = await self.embed_teams(ctx.channel)  # Should raise an error instead of sending back bools, SHIT code
        if not content:
            await ctx.send(f"Could not find teams, something has gone wrong!")

    @team.command(aliases=["n"])
    @Permissions.is_permitted()
    async def update(self, ctx: command.Context, team: discord.Role):
        """Updates a team's name to the new role"""
        team_lookup = await APIRequest.get(f"/team/discord-id?discord_id={team.id}")
        if team_lookup.status == 404:
            await ctx.send(f"Could not find a team with discord id: `{team.id}`")
            return
        elif team_lookup.status != 200:
            await ctx.send(f"Unable to receive data from the API, something has gone wrong!")
            return
        team_id = team_lookup.json["id"]
        name_response = await APIRequest.post(f"/team/name?new_name={team.name}&team_id={team_id}")
        if name_response.status != 200:
            await ctx.send(f"Something has gone wrong with the API!")
            return
        else:
            await ctx.send(f"Updated team name to `{team.name}`")

    @team.command(aliases=["c"])
    @Permissions.is_permitted()
    async def create(self, ctx: command.Context, discord_team_role: discord.Role, team_elo: int):
        """Creates a team"""
        response = await APIRequest.post(
            "/team/create",
            data={
                "team_name": discord_team_role.name,
                "discord_id": discord_team_role.id,
                "elo": team_elo
            }
        )
        if response.status == 403:
            await ctx.send(f"Could not authenticate with the API")
            return
        elif response.status == 409:
            await ctx.send(f"The team `{discord_team_role.name}` already exists!")
            return
        elif response.status != 200:
            await ctx.send(f"Unable to send the data to the API, something has gone wrong!")
            return
        team_id = response.json["extra"][0]["id"]
        await ctx.send(f"Created the team `{discord_team_role.name}` with ID: `{team_id}`")
        log.info(f"{ctx.author} ({ctx.author.id}) created the team {discord_team_role.name}, API id: {team_id}")

    @team.command(aliases=["d"])
    @Permissions.is_permitted()
    async def delete(self, ctx: command.Context, discord_team_role: discord.Role):
        """Deletes a team"""
        team_id = await APIRequest.get(f"/team/discord-id?discord_id={discord_team_role.id}")
        if team_id.status == 404:
            await ctx.send(f"Could not find a team with name: `{discord_team_role.name}`. "
                           f"It may have been renamed outside of the command functions or never added.")
            return
        elif team_id.status != 200:
            await ctx.send(f"Something went wrong on the API!")
            return
        team_id = team_id.json["id"]
        response = await APIRequest.post(f"/team/delete?team_id={team_id}")
        if response.status == 404:
            await ctx.send(f"Could not find that team!")
            return
        elif response.status == 403:
            await ctx.send(f"Could not authenticate with the API!")
            return
        await ctx.send(f"Deleted the team `{discord_team_role.name}`")
        log.info(f"{ctx.author} ({ctx.author.id}) deleted the team {discord_team_role.name}, API id: {team_id}")

    @team.command(aliases=["e"])
    @Permissions.is_permitted()
    async def elo(self, ctx: command.Context, discord_team_role: discord.Role, elo: int):
        response = await APIRequest.get(f"/team/discord-id?discord_id={discord_team_role.id}")
        if response.status == 404:
            await ctx.send(f"The team, {discord_team_role.name}, was not found!")
            return
        elif response.status != 200:
            await ctx.send("Something went wrong on the API!")
            return
        team_id = response.json["id"]
        elo_update = await APIRequest.post(f"/team/update-elo?new_elo={elo}&team_id={team_id}")
        if elo_update.status == 403:
            await ctx.send("Could not authenticate with the API!")
            return
        elif elo_update.status != 200:
            await ctx.send("Something went wrong on the API!")
            return
        else:
            await ctx.send(f"Updated {discord_team_role.name}'s elo to {elo}")
            log.info(f"{ctx.author} ({ctx.author.id}) updated {team_id}'s ({discord_team_role.name}) elo to {elo}")
            return

    @listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if before.name != after.name:
            team_lookup = await APIRequest.get(f"/team/discord-id?discord_id={after.id}")
            if team_lookup.status == 404:
                log.info(f"Could not find a team with discord id: \"{after.id}\"")
                return
            elif team_lookup.status != 200:
                log.info(f"Unable to receive data from the API, something has gone wrong!")
                return
            team_id = team_lookup.json["id"]
            name_response = await APIRequest.post(f"/team/name?new_name={after.name}&team_id={team_id}")
            if name_response.status != 200:
                log.info(f"Something has gone wrong with the API!")
                return
            else:
                log.info(f"Updated team \"{team_id}\" name to \"{after.name}\"")

    @listener()
    async def on_guild_role_delete(self, role: discord.Role):
        team_id = await APIRequest.get(f"/team/discord-id?discord_id={role.id}")
        if team_id.status != 200:
            return
        team_id = team_id.json["id"]
        response = await APIRequest.post(f"/team/delete?team_id={team_id}")
        if response.status == 200:
            log.info(f"Team \"{team_id}\" was deleted.")

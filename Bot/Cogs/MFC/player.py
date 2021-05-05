import logging

import discord

from Bot import APIRequest
from Bot.Cogs import BaseCog
from Bot.Cogs import command
from Bot.Cogs import listener
from Bot.Config.Permissions import Permissions

log = logging.getLogger(__name__)


class Player(BaseCog):
    base_endpoint = "/player"

    async def lookup_player_discord_id(self, discord_id: int):
        response = await APIRequest.get(self.base_endpoint + f"/discord-id?discord_id={discord_id}")
        if response.status == 200:
            return response.json
        else:
            log.info(f"Could not search up player by discord id \"{discord_id}\", status code: {response.status}")
            return None

    async def lookup_player_playfab_id(self, playfab_id: str):
        response = await APIRequest.get(self.base_endpoint + f"/playfab-id?playfab_id={playfab_id}")
        if response.status == 200:
            return response.json
        else:
            log.info(f"Could not search up player by playfab id \"{playfab_id}\", status code: {response.status}")
            return None

    @command.group(aliases=["p"])
    async def player(self, ctx: command.Context):
        """A group containing all MFC player related commands"""

    @player.command(aliases=["r"])
    async def register(self, ctx: command.Context, playfab_id: str):

        player = await self.lookup_player_playfab_id(playfab_id)
        member = ctx.author
        if await self.lookup_player_discord_id(member.id):
            await ctx.send(f"That member already exists!")
            return
        if not player:
            await ctx.send(f"No player with playfab id: `{playfab_id}` exists in the database.\n"
                           f"To rectify this please join a MFC server and type `!register`")
            return
        if discord_id := player["discord_id"]:
            guild: discord.Guild = ctx.guild
            if existing_player := await guild.get_member(discord_id):
                await ctx.send(f"The player {existing_player.name} has already been assigned that playfab id!")
                return
        response = await APIRequest.post(
            self.base_endpoint + f"/update-discord-id?discord_id={member.id}&player_id={player['id']}"
        )
        if response.status != 200:
            log.info(f"Could not register player, {response.status}: {response.json}")
            await ctx.send(f"Could not register player!")
            return
        else:
            log.info(f"{ctx.author} ({ctx.author.id}) registered {member} ({member.id}) "
                     f"to playfab id \"{playfab_id}\", API id \"{player['id']}\"")
            await ctx.send(f"Successfully registered and assigned {member.display_name} to playfab id `{playfab_id}`")
            return

    @player.command(aliases=["d"], name="discord")
    @Permissions.is_permitted()
    async def update_discord_id(self, ctx: command.Context, playfab_id: str, member: discord.Member):
        playfab_lookup = await self.lookup_player_playfab_id(playfab_id)
        if not playfab_lookup:
            await ctx.send(f"Could not find a player with either the provided playfab id.")
            return
        if playfab_lookup:
            response = await APIRequest.post(
                self.base_endpoint + f"/update-discord-id?discord_id={member.id}&player_id={playfab_lookup['id']}"
            )
            if response.status != 200:
                log.info(f"Could not register player, {response.status}: {response.json}")
                await ctx.send(f"Could not update player's discord id!")
                return
            else:
                log.info(f"{ctx.author} ({ctx.author.id}) assigned {member} ({member.id}) to playfab id "
                         f"\"{playfab_id}\", API id \"{response.json['extra'][0]['player_id']}")
                await ctx.send(
                    f"Successfully assigned {member.display_name} to playfab id `{playfab_id}`")
                return

    async def calculate_player_data(self, player_data: list[dict]) -> dict:

        """Calculates a list of API data like so:

        >>> [
        >>>      {
        >>>       "generated": "2021-05-05T19:54:01.308780+00:00",
        >>>       "message": null,
        >>>       "extra": null,
        >>>       "id": "eda931e5-b6f1-4ab2-8a58-4ab0b5c13371",
        >>>       "creation": "2021-05-05T19:46:54.222752+00:00",
        >>>       "modification": null,
        >>>       "team_id": "f25858f8-f738-4f11-be6a-01ccfb950b62",
        >>>       "team_number": 0,
        >>>       "round_id": "6c01d508-fd3f-43ca-86c4-f34b9fe576b0",
        >>>       "player_id": "4ed7ed5e-3a31-4a7b-a3b5-64ac4f46b108",
        >>>       "score": 39,
        >>>       "kills": 0,
        >>>       "deaths": 1,
        >>>       "assists": 2,
        >>>       "set_id": "4aece975-4ee9-4d91-bcb3-419bef2049bf",
        >>>       "match_id": "9324780a-a689-4d04-8cf8-8fb48bb029ac"
        >>>     }
        >>> ]
        """
        calculated_data = {
            "total-kills": 0,
            "total-deaths": 0,
            "total-assists": 0,
            "total-points": 0,
            "total-kda-r": 0,
            "total-kd": 0,
            "match-data": {}
        }

        match_rounds = {}
        for data in player_data:
            if not match_rounds.get(data["match_id"], None):
                match_rounds[data["match_id"]] = {}
                match = await APIRequest.get(f"/match/id?id={data['match_id']}")
                if match.status == 200:
                    team1_id = match.json["team1_id"]
                    team2_id = match.json["team2_id"]

                    async def get_team(team_id):
                        resp = await APIRequest.get(f"/team/id?id={team_id}")
                        if resp.status == 200:
                            return resp.json["team_name"]
                        else:
                            return None

                    match_rounds[data["match_id"]]["team_1"] = await get_team(team1_id)
                    match_rounds[data["match_id"]]["team_2"] = await get_team(team2_id)

            if not match_rounds[data["match_id"]].get(data["set_id"], None):
                match_rounds[data["match_id"]] |= {data["set_id"]: {}}
            calculated_data["total-kills"] += data["kills"]
            calculated_data["total-assists"] += data["assists"]
            calculated_data["total-deaths"] += data["deaths"]
            calculated_data["total-points"] += data["score"]
            if data["deaths"] > 0:
                kda_r = round((data["kills"] + data["assists"]) / data["deaths"], 2)
                kd = round(data["kills"] / data["deaths"], 2)
            else:
                kda_r = "Infinite"
                kd = "Infinite"
            round_data = {
                "kills": data["kills"],
                "deaths": data["deaths"],
                "assists": data["assists"],
                "score": data["score"],
                "kda-r": kda_r,
                "kd": kd
            }

            match_rounds[data["match_id"]][data["set_id"]] |= {data["round_id"]: round_data}

        calculated_data["match-data"] = match_rounds
        if calculated_data["total-deaths"] > 0:
            calculated_data["total-kda-r"] = \
                round((calculated_data["total-kills"] + calculated_data["total-assists"])
                      / calculated_data["total-deaths"], 2)
            calculated_data["total-kd"] = \
                round(calculated_data["total-kills"] / calculated_data["total-deaths"], 2)
        else:
            calculated_data["total-kda-r"] = "Infinite"
            calculated_data["total-kd"] = "Infinite"
        return calculated_data

    @player.command(aliases=["s"], name="stats")
    async def get_player_stats(self, ctx: command.Context, member: discord.Member):
        player_lookup = await APIRequest.get(f"/player/discord-id?discord_id={member.id}")
        if player_lookup.status == 404:
            await ctx.send(f"Could not find the player {member.mention}")
            return
        elif player_lookup.status != 200:
            await ctx.send(f"Unable to receive data from the API, something has gone wrong!")
            log.error(f"Unable to retrieve data from the API, status: \"{player_lookup.status}\", "
                      f"json: \"{player_lookup.json}\"")
            return
        player_rounds = await APIRequest.get(f"/round/rounds-played-by-player-id?round_player_id="
                                             f"{player_lookup.json['id']}")
        if player_rounds.status != 200:
            if player_rounds.status == 404:
                await ctx.send(f"Was unable to find rounds for that player...")
                return
            await ctx.send(f"Unable to receive data from the API, something has gone wrong!")
            log.error(f"Unable to retrieve data from the API, status: \"{player_lookup.status}\", "
                      f"json: \"{player_lookup.json}\"")
        else:
            stats_calculated = await self.calculate_player_data(player_rounds.json)
            stats_embed = self.bot.default_embed(
                author=self.bot.user,
                title=f"User stats for `{member.nick}`",
                url=APIRequest.api_url + f"/player/discord-id?discord_id={member.id}",
                description=f"""
                            __API Information__
                            **API Name:** `({player_lookup.json["player_name"][:100]})`,
                            **API ID:** `{player_lookup.json["id"]}`

                            __Stats__
                            **Score:** `{stats_calculated['total-points']}`
                            **Kills:** `{stats_calculated['total-kills']}`
                            **Assists:** `{stats_calculated['total-assists']}`
                            **Deaths:** `{stats_calculated['total-deaths']}`

                            __Ratios__
                            **KD/R:** `{stats_calculated['total-kd']}`
                            **KDA/R:** `{stats_calculated['total-kda-r']}`
                            """,
            )
            await ctx.send(embed=stats_embed)

import logging

from datetime import datetime
from datetime import timedelta

import discord

from Bot import APIRequest
from Bot.Cogs import BaseCog
from Bot.Cogs import command
from Bot.Config.Permissions import Permissions

log = logging.getLogger(__name__)


class Player(BaseCog):
    base_endpoint = "/player"

    cached_match_stats = {}

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

    async def calculate_player_data(self, matches: list[dict]) -> dict:

        players = {}
        for match in matches:
            for set in match["sets"]:
                for _round in set["rounds"]:
                    team1_list: list = _round["team1_players"] or []
                    team2_list: list = _round["team1_players"] or []
                    team1_list.extend(team2_list)
                    combined = team1_list
                    for player in combined:
                        if not players.get(player["player_id"], None):
                            players[player["player_id"]] = {
                                "score": 0,
                                "kills": 0,
                                "assists": 0,
                                "deaths": 0
                            }
                        player_dict = players[player["player_id"]]
                        player_dict["score"] += player["score"]
                        player_dict["kills"] += player["kills"]
                        player_dict["assists"] += player["assists"]
                        player_dict["deaths"] += player["deaths"]
                        kills = player_dict["kills"]
                        assists = player_dict["assists"]
                        deaths = player_dict["deaths"]
                        if deaths == 0:
                            player_dict["kda-r"] = 99999
                            player_dict["kd"] = 99999
                        else:
                            player_dict["kda"] = round((kills + assists) / deaths, 2)  # ???
                            player_dict["kd"] = round(kills / deaths, 2)  # ??? very strange int warning... idgaf

        return players

    @player.command(aliases=["t"], name="top")
    async def top_of_time_range(self, ctx: command.Context, time_range: str, top_of_type: str, amount: int = 10):
        """Gets the top 10 players of each time range and type and how many players stats to list out (amount)"""
        current_time = datetime.utcnow()
        time_ranges = {
            "day": lambda: current_time - timedelta(days=1),
            "week": lambda: current_time - timedelta(days=7),
            "month": lambda: current_time - timedelta(days=30),
            "all": "NO ACTION"
        }
        time_range = time_range.casefold().strip()
        if not time_ranges.get(time_range, None):
            await ctx.send(f"The time range argument MUST be one of the following: "
                           f"{', '.join(range.capitalize() for range in time_ranges.keys())}")
            return

        top_of_types = ("kd", "kda", "score", "kills", "deaths", "assists")
        top_of_type = top_of_type.strip().casefold()
        if not top_of_type in top_of_types:
            await ctx.send(f"The top of type argument MUST be one of the following: "
                           f"{', '.join(top_type.capitalize() for top_type in top_of_types)}")
            return
        start_time = current_time
        if time_range != "all":
            end_time = time_ranges.get(time_range)()
            match_data = await APIRequest.get(f"/match/all?start_time={start_time}?end_time={end_time}")
        else:
            match_data = await APIRequest.get(f"/match/all")
        if match_data.status != 200:
            await ctx.send(f"Could not get data from the API, something has gone wrong!")
            log.error(f"Could not reach the API, status: {match_data.status}, json: {match_data.json}")
            return

        player_data = await self.calculate_player_data(match_data.json)
        top_of_key_embeds = await self.top_of_key(ctx.guild, stats=player_data, key_name=top_of_type, amount=amount)
        for embed in top_of_key_embeds:
            await ctx.send(embed=embed)

    async def top_of_key(self, guild: discord.Guild, stats: dict, key_name: str, amount: int = 10) -> \
            list[discord.Embed]:

        player_field_data: dict[int: list[list[str, str]]] = {}

        players_added = 0
        # Could use enumerate instead of tracking above
        for player_api_data in reversed(sorted(stats.items(), key=lambda stat: stat[1][key_name])):
            if players_added == amount:
                break
            api_id = player_api_data[0]
            data = player_api_data[-1]
            api_player = await APIRequest.get(f"/player/id?id={api_id}")
            if api_player.status != 200:
                continue
            player_discord_id = api_player.json["discord_id"]
            if not player_discord_id:
                player_name = str(api_player.json["player_name"][:10])
            else:
                discord_player = guild.get_member(player_discord_id)
                if not discord_player:
                    discord_player = await guild.fetch_member(int(player_discord_id))
                    if not discord_player:
                        discord_player = '`' + str(api_player.json["player_name"][:10]) + '`'
                    else:
                        discord_player = discord_player.mention
                else:
                    discord_player = discord_player.mention
                player_name = discord_player
            players_added += 1
            if not player_field_data.get(players_added, None):
                player_field_data[players_added] = []
            player_field_data[players_added].append([player_name, data[key_name]])

        def generic_embed(player_position, player_names, player_data):
            description =f"{key_name.capitalize()} rankings for the top `{amount}` players\n\n"
            embed = self.bot.default_embed(title=f"{key_name.capitalize()} Statistics",
                                           description=description)
            player_position += "\n"
            player_names += "\n"
            player_data += "\n"
            embed.add_field(name="Ranking", value=player_position)
            embed.add_field(name="Name", value=player_names)
            embed.add_field(name=key_name.capitalize(), value=player_data)
            return embed

        ranking_field = ""
        names_field = ""
        data_field = ""
        send_embeds: list[discord.Embed] = []
        for ranking, players in player_field_data.items():
            for player in players:
                if (len(names_field) + (len(str(players)))) > 800:
                    send_embeds.append(generic_embed(ranking_field, names_field, data_field))
                    ranking_field = ""
                    names_field = ""
                    data_field = ""
                ranking_field += f"{ranking}.)\n"
                names_field += f"{player[0].strip()}\n"
                data_field += f"{player[1]}\n"

        if ranking_field and names_field and data_field:
            send_embeds.append(generic_embed(ranking_field, names_field, data_field))

        if not send_embeds:
            return [self.bot.default_embed(title=f"Could not find data in that range.")]
        return send_embeds

    @player.command(aliases=["s"], name="stats")
    async def get_player_stats(self, ctx: command.Context, member: discord.Member):
        """Gets stats for a single player"""
        player_lookup = await APIRequest.get(f"/player/discord-id?discord_id={member.id}")
        if player_lookup.status == 404:
            await ctx.send(f"Could not find the player {member.mention}")
            return
        elif player_lookup.status != 200:
            await ctx.send(f"Unable to receive data from the API, something has gone wrong!")
            log.error(f"Unable to retrieve data from the API, status: \"{player_lookup.status}\", "
                      f"json: \"{player_lookup.json}\"")
            return
        player_id = player_lookup.json["id"]
        player_rounds = await APIRequest.get(f"/match/all")
        if player_rounds.status != 200:
            if player_rounds.status == 404:
                await ctx.send(f"Was unable to find rounds for that player...")
                return
            await ctx.send(f"Unable to receive data from the API, something has gone wrong!")
            log.error(f"Unable to retrieve data from the API, status: \"{player_lookup.status}\", "
                      f"json: \"{player_lookup.json}\"")
        else:
            stats_calculated = await self.calculate_player_data(player_rounds.json)
            stats_calculated = stats_calculated.get(player_id, None)
            if not stats_calculated:
                await ctx.send("Was unable to fetch data for that member...")
                return
            stats_embed = self.bot.default_embed(
                author=self.bot.user,
                title=f"User stats for `{member.nick}`",
                url=APIRequest.api_url + f"/player/discord-id?discord_id={member.id}",
                description=f"""
                            __API Information__
                            **API Name:** `({player_lookup.json["player_name"][:100]})`,
                            **API ID:** `{player_lookup.json["id"]}`

                            __Stats__
                            **Score:** `{stats_calculated['score']}`
                            **Kills:** `{stats_calculated['kills']}`
                            **Assists:** `{stats_calculated['assists']}`
                            **Deaths:** `{stats_calculated['deaths']}`

                            __Ratios__
                            **KD/R:** `{stats_calculated['kd']}`
                            **KDA/R:** `{stats_calculated['kda']}`
                            """,
            )
            await ctx.send(embed=stats_embed)

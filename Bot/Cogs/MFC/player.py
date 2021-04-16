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
    async def register(self, ctx: command.Context, member: discord.Member, playfab_id: str):

        player = await self.lookup_player_playfab_id(playfab_id)
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

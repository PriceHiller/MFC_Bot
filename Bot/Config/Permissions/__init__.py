import json

from discord import Member
from discord.ext import commands

from Bot import config_path

config_dict: dict = json.loads(open(config_path).read())


class BasePerm:

    def __init__(self, user_id: int):
        self.id = user_id


class Admin(BasePerm):
    permitted_commands = config_dict["MFC-Guild"]["Admins"]["Commands"]

    def __init__(self, role_id: int):
        super().__init__(role_id)


class Moderator(BasePerm):
    permitted_commands = config_dict["MFC-Guild"]["Moderators"]["Commands"]

    def __init__(self, role_id: int):
        super().__init__(role_id)


class UserPerm(BasePerm):
    def __init__(self, user_id: int, permitted_commands: list[str]):
        self.permitted_commands = permitted_commands
        super().__init__(user_id)


class Permissions:
    admins: list[Admin] = [Admin(int(role_id)) for role_id in config_dict["MFC-Guild"]["Admins"]["Ids"]]
    moderators: list[Moderator] = [Moderator(int(role_id)) for role_id in config_dict["MFC-Guild"]["Moderators"]["Ids"]]
    users = [UserPerm(user_id=int(user_id), permitted_commands=perms) for user_id, perms, in
             config_dict["MFC-Guild"]["Specific-User-Perm"].items()]

    @staticmethod
    async def check_perms(ctx: commands.Context, command_name: str):
        member = ctx.author
        check_roles = [Permissions.admins, Permissions.moderators]
        if ctx.guild:
            for internal_role in check_roles:
                for role in internal_role:
                    for discord_role in member.roles:
                        if role.id == discord_role.id and \
                                ("*" in role.permitted_commands or command_name in role.permitted_commands):
                            return True
        for user in Permissions.users:
            if user.id == member.id and \
                    ("*" in user.permitted_commands or command_name in user.permitted_commands):
                return True
        await ctx.send(f"{ctx.author.mention}, you lack the permissions required to run this command!", delete_after=10)
        return False

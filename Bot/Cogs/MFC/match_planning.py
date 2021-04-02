from discord import utils
from discord import guild

from Bot.Cogs import BaseCog
from Bot.Cogs import command


class MatchPlanning(BaseCog):

    @command.group()
    async def mfc(self, ctx: command.Context):
        ...

    @mfc.command(aliases=["p"])
    async def plan(self, ctx: command.Context, *days: str):
        """Shit code for a shit person. Needs a MAJOR refactor once everything is good to go."""
        if not str(ctx.author.id) == "172503043818913794":
            return

        plan_days = {
            "sunday": False,
            "monday": False,
            "tuesday": False,
            "wednesday": False,
            "thursday": False,
            "friday": False,
            "saturday": False,
        }

        found_plan_day = False
        for day in days:
            day = day.casefold()
            if len(day) < 3:
                continue
            for key_day in plan_days.keys():
                if key_day[:3] == day[:3]:
                    plan_days[key_day] = True
                    found_plan_day = True
        if not found_plan_day:
            await ctx.send("Please provide a plan day, at least the first three letters of any day (e.g. monday)")
            return
        for plan_day in plan_days.items():
            if plan_day[1]:
                message = await ctx.send(f"{plan_day[0].capitalize()}: :eight: for 8est, :nine: for 9est, "
                                         f":keycap_ten: for 10est")
                await message.add_reaction("8️⃣")
                await message.add_reaction("9️⃣")
                await message.add_reaction("🔟")

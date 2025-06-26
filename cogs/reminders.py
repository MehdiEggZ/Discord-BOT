# cogs/reminders.py
import discord
from discord.ext import commands
import asyncio
import re
from datetime import datetime, timedelta

class Reminders(commands.Cog):
    """Commands for setting reminders."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def parse_time(self, time_str: str) -> int | None:
        parts = re.compile(r"(\d+)(s|m|h|d)").match(time_str)
        if not parts: return None
        count, unit = int(parts.groups()[0]), parts.groups()[1]
        if unit == 's': return count
        if unit == 'm': return count * 60
        if unit == 'h': return count * 3600
        if unit == 'd': return count * 86400
        return None

    @commands.command(name="remindme", aliases=['remind'], help="Sets a reminder. E.g., !remindme 10m check my code")
    async def remindme(self, ctx: commands.Context, time_str: str, *, reason: str = "No reason provided"):
        seconds = self.parse_time(time_str.lower())
        if seconds is None:
            embed = discord.Embed(title="❌ Invalid Time Format", color=discord.Color.red(),
                                  description="Use: `10s`, `15m`, `2h`, `3d`")
            return await ctx.reply(embed=embed)

        future_time = datetime.now() + timedelta(seconds=seconds)
        embed = discord.Embed(title="⏰ Reminder Set!", color=discord.Color.blue(),
                              description=f"I will remind you about: **{reason}**")
        embed.set_footer(text=f"Reminder will be sent at {future_time.strftime('%Y-%m-%d %I:%M %p')}")
        await ctx.reply(embed=embed)
        
        await asyncio.sleep(seconds)
        
        reminder_embed = discord.Embed(title="⏰ Your Reminder!", color=discord.Color.green(),
                                       description=f"You asked me to remind you about:\n**{reason}**",
                                       timestamp=ctx.message.created_at)
        reminder_embed.set_footer(text=f"Reminder was set in server: {ctx.guild.name}")
        try:
            await ctx.author.send(embed=reminder_embed)
        except discord.Forbidden:
            await ctx.reply(f"Hey {ctx.author.mention}, here's your reminder!", embed=reminder_embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Reminders(bot))
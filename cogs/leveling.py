# cogs/leveling.py
import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from collections import defaultdict

# --- Data Management ---
LEVELS_FILE = "levels.json"

def load_levels():
    """Loads level data from a file, ensuring nested dictionaries."""
    if os.path.exists(LEVELS_FILE):
        with open(LEVELS_FILE, 'r') as f:
            try:
                # Load the data and ensure each guild's data is a defaultdict
                data = json.load(f)
                return defaultdict(lambda: defaultdict(lambda: {"xp": 0, "level": 1}), 
                                   {gid: defaultdict(lambda: {"xp": 0, "level": 1}, udata) for gid, udata in data.items()})
            except json.JSONDecodeError:
                pass # Fallback to new defaultdict if file is empty/corrupt
    # If file doesn't exist or is invalid, create a new nested defaultdict structure
    return defaultdict(lambda: defaultdict(lambda: {"xp": 0, "level": 1}))

def save_levels(levels_data):
    """Saves level data to a file."""
    with open(LEVELS_FILE, 'w') as f:
        # Convert defaultdicts to regular dicts for clean JSON saving
        json.dump({k: dict(v) for k, v in levels_data.items()}, f, indent=4)

class Leveling(commands.Cog):
    """Commands for the server's XP and leveling system."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.levels_data = load_levels()
        self.xp_cooldowns = defaultdict(dict)

    def get_xp_for_level(self, level: int) -> int:
        """Calculates the total XP needed to reach a certain level."""
        if level <= 0: return 0
        return 5 * (level**2) + (50 * level) + 100

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        guild_id = str(message.guild.id)
        user_id = str(message.author.id)
        
        # Cooldown check
        now = asyncio.get_event_loop().time()
        if now < self.xp_cooldowns[guild_id].get(user_id, 0):
            return

        # --- THIS IS THE FIX ---
        # The defaultdict structure now correctly handles creating new users automatically,
        # so the KeyError will no longer occur.
        self.xp_cooldowns[guild_id][user_id] = now + 60
        xp_to_add = random.randint(15, 25)
        self.levels_data[guild_id][user_id]["xp"] += xp_to_add
        
        current_xp = self.levels_data[guild_id][user_id]["xp"]
        current_level = self.levels_data[guild_id][user_id]["level"]
        xp_for_next_level = self.get_xp_for_level(current_level)

        if current_xp >= xp_for_next_level:
            self.levels_data[guild_id][user_id]["level"] += 1
            new_level = self.levels_data[guild_id][user_id]["level"]
            try:
                await message.channel.send(f"🎉 Congratulations {message.author.mention}, you have reached **Level {new_level}**!")
            except discord.Forbidden:
                pass

        # Save data periodically
        if random.randint(1, 5) == 1:
            save_levels(self.levels_data)
    
    @commands.command(name="rank", help="Shows your current level and XP.")
    async def rank(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)

        user_data = self.levels_data[guild_id][user_id]
        current_xp = user_data["xp"]
        current_level = user_data["level"]
        
        xp_for_next_level = self.get_xp_for_level(current_level)
        xp_for_current_level = self.get_xp_for_level(current_level - 1)
        
        xp_in_level = current_xp - xp_for_current_level
        xp_needed_for_next = xp_for_next_level - xp_for_current_level
        
        progress = max(0, min(1, xp_in_level / xp_needed_for_next if xp_needed_for_next > 0 else 0))
        progress_bar = "▓" * int(progress * 10) + "░" * (10 - int(progress * 10))

        embed = discord.Embed(title=f"Rank for {member.display_name}", color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Level", value=f"**{current_level}**", inline=True)
        embed.add_field(name="Total XP", value=f"`{current_xp}`", inline=True)
        embed.add_field(name="Progress", value=f"`{xp_in_level} / {xp_needed_for_next} XP`\n`[{progress_bar}]`", inline=False)
        
        await ctx.reply(embed=embed)

    @commands.command(name="leaderboard", aliases=['lb'], help="Shows the server's top 10 most active members.")
    async def leaderboard(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)
        if guild_id not in self.levels_data or not self.levels_data[guild_id]:
            return await ctx.reply("There is no leaderboard data for this server yet.")

        # --- THIS IS THE FIX ---
        # Filter out any potentially malformed entries before sorting
        valid_users = {uid: data for uid, data in self.levels_data[guild_id].items() if isinstance(data, dict) and 'xp' in data}
        sorted_users = sorted(valid_users.items(), key=lambda item: item[1]['xp'], reverse=True)

        embed = discord.Embed(title=f"🏆 XP Leaderboard for {ctx.guild.name}", color=discord.Color.gold())
        
        description = ""
        for i, (user_id, data) in enumerate(sorted_users[:10]):
            try:
                user = await self.bot.fetch_user(int(user_id))
                user_name = user.name
            except discord.NotFound:
                user_name = "Unknown User"
            
            level, xp = data.get('level', 1), data.get('xp', 0)
            emoji = ""
            if i == 0: emoji = "🥇"
            elif i == 1: emoji = "🥈"
            elif i == 2: emoji = "🥉"
            else: emoji = f"**{i+1}.**"
            description += f"{emoji} **{user_name}** - Level {level} (`{xp}` XP)\n"

        if not description:
            return await ctx.reply("There is no one on the leaderboard yet!")

        embed.description = description
        await ctx.reply(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Leveling(bot))

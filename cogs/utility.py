# cogs/utility.py
import discord
from discord.ext import commands
from discord.ui import View, Select
import time
from config import PREFIX
import asyncio
import random

# --- Helper Functions for Embeds ---
def create_main_help_embed(bot: commands.Bot) -> discord.Embed:
    desc = (
        "**MehdiBOT is the perfect bot for your server, packed with features for moderation, music, and more!**\n\n"
        f"You can start listening to music by joining a voice channel and typing:\n`{PREFIX}play [song name or link]`\n\n"
        f"To view help on a specific command or category, run:\n`{PREFIX}help <command>` or select an option from the menu below."
    )
    embed = discord.Embed(title="🤖 MehdiBOT Help Desk", description=desc, color=0x00bfff)
    embed.add_field(name="Important Link", value="[Invite Me](https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot)", inline=False)
    embed.set_thumbnail(url=bot.user.display_avatar.url).set_footer(text=f"Bot developed by Mehdi | Total Commands: {len(bot.commands)}")
    return embed

def create_cog_help_embed(cog: commands.Cog) -> discord.Embed:
    # --- UPDATED EMOJI MAP ---
    emoji_map = {
        "Moderation": "🛡️", "Utility": "⚙️", "Translate": "🌐", "Music": "🎵", 
        "Reminders": "⏰", "Owner": "👑", "Alias": "🔗", "Leveling": "🏆", 
        "Converters": "💱", "Gaming": "🎮", "Twenty Questions": "🤔"
    }
    embed = discord.Embed(title=f"{emoji_map.get(cog.qualified_name, '⭐')} {cog.qualified_name} Commands", description=cog.description or "Here are the commands in this category:", color=0x00bfff)
    for cmd in cog.get_commands():
        if not cmd.hidden:
            embed.add_field(name=f"`{PREFIX}{cmd.name} {cmd.signature}`", value=cmd.help or "No description provided.", inline=False)
    embed.set_footer(text="Arguments in <> are required, [] are optional.")
    return embed

# --- Dropdown and View for the Help Command ---
class HelpDropdown(discord.ui.Select):
    def __init__(self, bot: commands.Bot, author_id: int):
        self.bot = bot
        options = [discord.SelectOption(label="Home", description="Return to the main help menu.", emoji="🏠")]
        # --- UPDATED EMOJI MAP ---
        emoji_map = {
            "Moderation": "🛡️", "Utility": "⚙️", "Translate": "🌐", "Music": "🎵", 
            "Reminders": "⏰", "Owner": "👑", "Alias": "🔗", "Leveling": "🏆", 
            "Converters": "💱", "Gaming": "🎮", "TwentyQuestions": "🤔"
        }
        for cog_name, cog in bot.cogs.items():
            if cog.get_commands():
                if cog_name == "Owner" and bot.owner_id != author_id:
                    continue
                cog_desc = cog.description or f"Commands in the {cog_name} category."
                if len(cog_desc) > 100:
                    cog_desc = cog_desc[:97] + "..."
                options.append(discord.SelectOption(label=cog_name, description=cog_desc, emoji=emoji_map.get(cog_name, "⭐")))
        super().__init__(placeholder="Select a category to see its commands...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_cog_name = self.values[0]
        if selected_cog_name == "Home":
            new_embed = create_main_help_embed(self.bot)
            if new_embed.fields: new_embed.fields[0].value = new_embed.fields[0].value.format(bot=self.bot)
        else:
            cog = self.bot.get_cog(selected_cog_name)
            new_embed = create_cog_help_embed(cog)
        await interaction.response.edit_message(embed=new_embed)

class HelpView(View):
    def __init__(self, bot: commands.Bot, author_id: int):
        super().__init__(timeout=180.0)
        self.author_id = author_id
        self.add_item(HelpDropdown(bot, author_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This isn't for you!", ephemeral=True)
            return False
        return True

# --- The Main Cog ---
class Utility(commands.Cog):
    """Useful and miscellaneous commands."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="help", aliases=['h'], help="Shows this interactive help message.")
    async def help_command(self, ctx: commands.Context, *, command_name: str = None):
        if command_name:
            command = self.bot.get_command(command_name)
            if not command or command.hidden: return await ctx.reply(f"❌ Command `{command_name}` not found.")
            embed = discord.Embed(title=f"🔎 Help for `{PREFIX}{command.name}`", description=command.help or "No description provided.", color=0x00bfff)
            embed.add_field(name="Usage", value=f"`{PREFIX}{command.name} {command.signature}`", inline=False)
            if command.aliases: embed.add_field(name="Aliases", value=", ".join(f"`{alias}`" for alias in command.aliases), inline=False)
            embed.set_footer(text="Arguments in <> are required, [] are optional.")
            await ctx.reply(embed=embed)
        else:
            initial_embed = create_main_help_embed(self.bot)
            if initial_embed.fields: initial_embed.fields[0].value = initial_embed.fields[0].value.format(bot=self.bot)
            view = HelpView(self.bot, ctx.author.id)
            await ctx.reply(embed=initial_embed, view=view)

    # ... (The rest of the utility commands: ping, userinfo, etc. remain the same)
    @commands.command(name="ping", help="Checks the bot's latency.")
    async def ping(self, ctx: commands.Context):
        start_time, message = time.monotonic(), await ctx.reply("Pinging...")
        end_time, latency, response_time = time.monotonic(), self.bot.latency * 1000, (time.monotonic() - start_time) * 1000
        embed = discord.Embed(title="🏓 Pong!", color=discord.Color.green()).add_field(name="API Latency", value=f"`{latency:.2f}ms`").add_field(name="Response Time", value=f"`{response_time:.2f}ms`")
        await message.edit(content=None, embed=embed)
        
    @commands.command(name="userinfo", aliases=["whois"], help="Displays information about a user.")
    async def userinfo(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        now = discord.utils.utcnow()
        created_days, joined_days = (now - member.created_at).days, (now - member.joined_at).days
        embed = discord.Embed(title=f"👤 User Information for {member}", color=member.color).set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Username", value=member.name, inline=True).add_field(name="ID", value=f"`{member.id}`", inline=True).add_field(name="Status", value=str(member.status).title(), inline=True)
        embed.add_field(name="Top Role", value=member.top_role.mention, inline=True).add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:D>\n({created_days} days ago)", inline=True).add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:D>\n({joined_days} days ago)", inline=True)
        roles = [role.mention for role in reversed(member.roles) if role.name != "@everyone"]
        if roles: embed.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles) if len(roles) <= 10 else "Too many to show", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.reply(embed=embed)
        
    @commands.command(name="serverinfo", aliases=["server"], help="Displays information about the server.")
    async def serverinfo(self, ctx: commands.Context):
        guild = ctx.guild
        embed = discord.Embed(title=f"**{guild.name}** Server Information", color=discord.Color.random())
        if guild.icon: embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="👑 Owner", value=guild.owner.mention, inline=True).add_field(name="🆔 Server ID", value=f"`{guild.id}`", inline=True).add_field(name="📆 Created On", value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)
        embed.add_field(name="👥 Members", value=f"**{guild.member_count}** total", inline=True).add_field(name="💬 Channels", value=f"**{len(guild.text_channels)}** Text | **{len(guild.voice_channels)}** Voice", inline=True).add_field(name="✨ Roles", value=f"**{len(guild.roles)}**", inline=True)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.reply(embed=embed)
        
    @commands.command(name="avatar", aliases=["av", "pfp"], help="Shows a user's avatar.")
    async def avatar(self, ctx: commands.Context, *, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(title=f"🖼️ Avatar for {member.display_name}", color=member.color).set_image(url=member.display_avatar.with_size(1024))
        await ctx.reply(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))

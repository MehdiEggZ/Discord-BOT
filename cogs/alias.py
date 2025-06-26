# cogs/alias.py
import discord
from discord.ext import commands
import json
import os

# --- Alias File Management ---
ALIAS_FILE = "aliases.json"

def load_aliases():
    """Loads the alias data from the JSON file."""
    if not os.path.exists(ALIAS_FILE):
        return {}
    with open(ALIAS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_aliases(aliases_data):
    """Saves the alias data to the JSON file."""
    with open(ALIAS_FILE, 'w') as f:
        json.dump(aliases_data, f, indent=4)

class Alias(commands.Cog):
    """Manage custom command aliases for your server."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="alias", help="Manages server-specific command aliases. # E.g .alias set m mute")
    @commands.has_permissions(manage_guild=True) # Only members who can manage the server can set aliases
    async def alias(self, ctx: commands.Context):
        """Base command for alias management. Shows a list of aliases if no subcommand is used."""
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self.alias_list)

    @alias.command(name="set", help="Sets a custom alias for a command. Usage: .alias set <alias> <command>")
    async def alias_set(self, ctx: commands.Context, alias_name: str, *, command_name: str):
        """Sets a new command alias for this server."""
        command = self.bot.get_command(command_name)
        if command is None:
            return await ctx.reply(f"❌ The command `{command_name}` does not exist.")
        
        # Prevent aliasing command groups or the alias command itself
        if isinstance(command, commands.Group) or command.name in ['alias', 'help']:
             return await ctx.reply(f"❌ You cannot create an alias for `{command.name}`.")
             
        all_aliases = load_aliases()
        server_id = str(ctx.guild.id)

        if server_id not in all_aliases:
            all_aliases[server_id] = {}

        # Check if the alias name is already in use
        if self.bot.get_command(alias_name) or alias_name in all_aliases[server_id]:
            return await ctx.reply(f"❌ `{alias_name}` is already a command or an alias in this server.")

        all_aliases[server_id][alias_name.lower()] = command.name
        save_aliases(all_aliases)
        
        # Reload the bot's internal alias cache
        if hasattr(self.bot, 'reload_aliases'):
            self.bot.reload_aliases()

        await ctx.reply(f"✅ The alias `{ctx.prefix}{alias_name}` has been set for the command `{ctx.prefix}{command.name}`.")

    @alias.command(name="remove", help="Removes a custom alias. Usage: .alias remove <alias>")
    async def alias_remove(self, ctx: commands.Context, alias_name: str):
        """Removes a command alias for this server."""
        all_aliases = load_aliases()
        server_id = str(ctx.guild.id)

        if server_id not in all_aliases or alias_name.lower() not in all_aliases[server_id]:
            return await ctx.reply(f"❌ The alias `{alias_name}` does not exist in this server.")

        del all_aliases[server_id][alias_name.lower()]
        save_aliases(all_aliases)

        # Reload the bot's internal alias cache
        if hasattr(self.bot, 'reload_aliases'):
            self.bot.reload_aliases()
            
        await ctx.reply(f"✅ The alias `{alias_name}` has been removed.")

    @alias.command(name="list", help="Shows all custom aliases for this server.")
    async def alias_list(self, ctx: commands.Context):
        """Lists all custom command aliases for this server."""
        all_aliases = load_aliases()
        server_id = str(ctx.guild.id)

        if server_id not in all_aliases or not all_aliases[server_id]:
            return await ctx.reply("This server has no custom aliases set.")

        embed = discord.Embed(title=f"Custom Aliases for {ctx.guild.name}", color=discord.Color.blue())
        description = ""
        for alias, command in all_aliases[server_id].items():
            description += f"`{ctx.prefix}{alias}`  ➔  `{ctx.prefix}{command}`\n"
        
        embed.description = description
        await ctx.reply(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Alias(bot))

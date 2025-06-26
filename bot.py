# bot.py
import discord
from discord.ext import commands, tasks
import os
import asyncio
import logging
from itertools import cycle
from config import TOKEN, PREFIX, OWNER_ID
import json

# --- Alias File Management ---
ALIAS_FILE = "aliases.json"

def load_aliases():
    """Loads alias data from the JSON file."""
    if not os.path.exists(ALIAS_FILE):
        return {}
    with open(ALIAS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

# --- Custom Bot Class to Handle Aliases ---
class MehdiBOT(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aliases_cache = load_aliases()

    def reload_aliases(self):
        """Method to reload the alias cache from the file."""
        self.aliases_cache = load_aliases()

    async def get_context(self, message, *, cls=commands.Context):
        """
        Overrides the default get_context to check for and apply custom aliases.
        """
        if message.guild and message.content.startswith(self.command_prefix):
            server_id = str(message.guild.id)
            server_aliases = self.aliases_cache.get(server_id, {})

            if server_aliases:
                potential_alias = message.content[len(self.command_prefix):].split(' ')[0].lower()
                
                if potential_alias in server_aliases:
                    real_command = server_aliases[potential_alias]
                    message.content = message.content.replace(potential_alias, real_command, 1)

        return await super().get_context(message, cls=cls)

# --- Logging Setup ---
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler, file_handler = logging.StreamHandler(), logging.FileHandler(filename='discord_bot.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
file_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
logger.addHandler(file_handler)

# --- Custom Exception ---
class DMsNotAllowed(commands.CheckFailure):
    pass

# --- Bot Instantiation (Using the custom class) ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = MehdiBOT(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None,
    case_insensitive=True,
    owner_id=OWNER_ID
)

@bot.check
async def block_dms(ctx: commands.Context):
    if ctx.guild is None:
        raise DMsNotAllowed()
    return True

# --- Dynamic Status ---
status_list = [
    {"type": "watching", "text": "Developed by Mehdi"},
    {"type": "listening", "text": "Developed by Mehdi"},
    {"type": "playing", "text": "Developed by Mehdi"},
    {"type": "streaming", "text": "Developed by Mehdi"}
]
status_cycle = cycle(status_list)

@tasks.loop(seconds=15)
async def change_status():
    current_status = next(status_cycle)
    activity_type_str, text = current_status['type'], current_status['text']
    activity = None
    if activity_type_str == "playing": activity = discord.Game(name=text)
    elif activity_type_str == "watching": activity = discord.Activity(type=discord.ActivityType.watching, name=text)
    elif activity_type_str == "listening": activity = discord.Activity(type=discord.ActivityType.listening, name=text)
    elif activity_type_str == "streaming": activity = discord.Streaming(name=text, url="https://www.twitch.tv/monstercat")
    if activity: await bot.change_presence(activity=activity)

@bot.event
async def on_ready():
    print("--------------------------------------------------")
    logger.info(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    logger.info(f"🔗 Invite Link: https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot")
    print("--------------------------------------------------")
    if not change_status.is_running():
        change_status.start()

@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, DMsNotAllowed): await ctx.author.send("❌ Commands are only allowed in servers, not in DMs."); return
    if isinstance(error, commands.NotOwner): await ctx.reply("❌ This is an owner-only command."); return
    if isinstance(error, commands.CommandNotFound): return
    if isinstance(error, commands.MissingRequiredArgument): await ctx.reply(f"❌ **Missing Argument!** See `{PREFIX}help {ctx.command}` for details.")
    elif isinstance(error, commands.MissingPermissions): await ctx.reply("❌ **Permission Denied!**")
    elif isinstance(error, commands.BotMissingPermissions): await ctx.reply("❌ **I can't do that!**")
    elif isinstance(error, commands.MemberNotFound): await ctx.reply("❌ **Member Not Found.**")
    elif isinstance(error, commands.CommandOnCooldown): await ctx.reply(f"⏳ This command is on cooldown. Please try again in {error.retry_after:.2f} seconds.")
    else:
        logger.error(f"An unhandled error occurred in command '{ctx.command}': {error}")
        await ctx.reply(f"An unexpected error occurred.")

async def main():
    async with bot:
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and filename != '__init__.py':
                try:
                    await bot.load_extension(f'cogs.{filename[:-3]}')
                    logger.info(f"✔️ Successfully loaded cog: {filename[:-3]}")
                except Exception as e:
                    logger.error(f'❌ Failed to load extension {filename[:-3]}: {e}')
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
    except discord.errors.LoginFailure:
        logger.error("❌ Invalid Discord Token. Please check your `config.py` file.")

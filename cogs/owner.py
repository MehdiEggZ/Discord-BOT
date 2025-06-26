# cogs/owner.py
import discord
from discord.ext import commands
import asyncio
import json
import os
import re
import random

# --- Whitelist File Management ---
WHITELIST_FILE = "whitelist.json"
SPAM_WORDS_FILE = "spam.txt"

def load_whitelist():
    """Loads the whitelist from a JSON file."""
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_whitelist(user_ids):
    """Saves the whitelist to a JSON file."""
    with open(WHITELIST_FILE, 'w') as f:
        json.dump(user_ids, f, indent=4)

# --- Custom Check for Commands ---
def is_owner_or_whitelisted():
    """A custom check to see if the user is the bot owner or is in the whitelist file."""
    async def predicate(ctx: commands.Context) -> bool:
        if await ctx.bot.is_owner(ctx.author):
            return True
        whitelisted_users = load_whitelist()
        return ctx.author.id in whitelisted_users
    return commands.check(predicate)


class Owner(commands.Cog):
    """Owner-only and whitelisted-user commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- Whitelist Command Group ---
    @commands.group(name="whitelist", help="Manages users who can use privileged commands.", invoke_without_command=True)
    @commands.is_owner()
    async def whitelist(self, ctx: commands.Context, user: discord.Member = None):
        if user:
            await ctx.invoke(self.whitelist_add, user=user)
            return

        if ctx.invoked_subcommand is None:
            whitelisted_users = load_whitelist()
            if not whitelisted_users:
                return await ctx.reply("The whitelist is currently empty.")

            embed = discord.Embed(title="👑 Whitelisted Users", color=discord.Color.blue())
            user_mentions = [f"- {(self.bot.get_user(uid) or 'Unknown User').mention} (`{uid}`)" for uid in whitelisted_users]
            embed.description = "\n".join(user_mentions)
            await ctx.reply(embed=embed)

    @whitelist.command(name="add", help="Adds a user to the whitelist.")
    @commands.is_owner()
    async def whitelist_add(self, ctx: commands.Context, user: discord.Member):
        whitelisted_users = load_whitelist()
        if user.id in whitelisted_users:
            return await ctx.reply(f"❌ **{user.name}** is already on the whitelist.")
        
        whitelisted_users.append(user.id)
        save_whitelist(whitelisted_users)
        await ctx.reply(f"✅ Added **{user.name}** to the whitelist.")

    @whitelist.command(name="remove", help="Removes a user from the whitelist.")
    @commands.is_owner()
    async def whitelist_remove(self, ctx: commands.Context, user: discord.Member):
        whitelisted_users = load_whitelist()
        if user.id not in whitelisted_users:
            return await ctx.reply(f"❌ **{user.name}** is not on the whitelist.")
            
        whitelisted_users.remove(user.id)
        save_whitelist(whitelisted_users)
        await ctx.reply(f"✅ Removed **{user.name}** from the whitelist.")

    @commands.command(name="unwhitelist", help="Removes a user from the whitelist.")
    @commands.is_owner()
    async def unwhitelist(self, ctx: commands.Context, user: discord.Member):
        await ctx.invoke(self.whitelist_remove, user=user)

    # --- Spam Command Suite ---
    @commands.command(name="spam", help="Spams a user with DMs. Usage: .spam @user <amount>")
    @is_owner_or_whitelisted()
    async def spam(self, ctx: commands.Context, user: discord.Member, amount: int):
        """Spams a user with direct messages from a predefined list."""
        if not os.path.exists(SPAM_WORDS_FILE):
            return await ctx.reply(f"❌ The `{SPAM_WORDS_FILE}` file was not found.")
        with open(SPAM_WORDS_FILE, 'r') as f:
            words = [line.strip() for line in f if line.strip()]
        if not words:
            return await ctx.reply(f"❌ The `{SPAM_WORDS_FILE}` file is empty.")
        if amount > 100:
            return await ctx.reply("❌ You can only spam a maximum of 100 messages at a time.")
            
        success_count, failure_count = 0, 0
        progress_message = await ctx.reply(f"💥 Starting to spam **{user.name}** with {amount} messages...")
        for i in range(amount):
            try:
                await user.send(random.choice(words))
                success_count += 1
                await asyncio.sleep(0.5)
            except (discord.Forbidden, discord.HTTPException):
                failure_count += 1
                break 
        if failure_count > 0:
            result_message = f"💥 Spam attempt finished.\n✅ Sent {success_count} messages.\n❌ Failed to send {failure_count} message(s). The user likely has DMs disabled."
        else:
            result_message = f"💥 Spam finished!\n✅ Successfully sent {success_count} messages to **{user.name}**."
        await progress_message.edit(content=result_message)

    @commands.command(name="delspam", help="Deletes the bot's last DMs to a user. Usage: .delspam @user <amount>")
    @is_owner_or_whitelisted()
    async def delspam(self, ctx: commands.Context, user: discord.Member, amount: int):
        """Deletes the last 'amount' of messages the bot sent to a user's DMs."""
        if amount > 100:
            return await ctx.reply("❌ You can only delete a maximum of 100 messages at a time.")

        progress_message = await ctx.reply(f"🧹 Attempting to delete the last {amount} messages sent to **{user.name}**...")
        dm_channel = await user.create_dm()
        deleted_count = 0
        async for message in dm_channel.history(limit=200):
            if deleted_count >= amount: break
            if message.author == self.bot.user:
                try:
                    await message.delete()
                    deleted_count += 1
                    await asyncio.sleep(0.5)
                except (discord.Forbidden, discord.HTTPException):
                    break
        await progress_message.edit(content=f"🧹 Cleanup complete!\n✅ Successfully deleted {deleted_count} message(s).")

    @commands.command(name="sspam", help="Pings a user in the channel. Usage: .sspam @user <amount>")
    @is_owner_or_whitelisted()
    async def sspam(self, ctx: commands.Context, user: discord.Member, amount: int):
        """Spams a user by pinging them repeatedly in the current channel."""
        if amount > 50:
            return await ctx.reply("❌ To prevent issues, please keep the server spam amount below 50.")
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        for i in range(amount):
            # --- UPDATED: Removed the "Hey" text ---
            await ctx.send(f"{user.mention}", delete_after=5)
            await asyncio.sleep(1)
        await ctx.send(f"Finished spamming {user.mention}.", delete_after=10)

    # --- Announcement Commands ---
    @commands.command(name="uannounce", help="Sends a DM to a specific user. [gif_url] is optional.")
    @is_owner_or_whitelisted()
    async def user_announce(self, ctx: commands.Context, user: discord.User, *, message: str):
        gif_url = None
        url_match = re.search(r'(https?://\S+\.(?:png|jpg|jpeg|gif))$', message)
        if url_match:
            gif_url = url_match.group(0)
            message = message[:url_match.start()].strip()
        announce_embed = discord.Embed(
            title="✨ Announcement from MehdiBOT's Developer ✨", description=f"**{message}**",
            color=0x7289DA, timestamp=ctx.message.created_at)
        if gif_url: announce_embed.set_image(url=gif_url)
        announce_embed.set_footer(text=f"Sent by: {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        try:
            await user.send(embed=announce_embed)
            await ctx.reply(f"✅ Successfully sent the announcement to **{user.name}**.")
        except discord.Forbidden:
            await ctx.reply(f"❌ Could not send message to **{user.name}**. They may have DMs disabled.")
        except Exception as e: await ctx.reply(f"❌ An unexpected error occurred: {e}")

    @commands.command(name="gannounce", help="Sends a DM to all users. [gif_url] is optional.")
    @is_owner_or_whitelisted()
    async def global_announce(self, ctx: commands.Context, *, message: str):
        gif_url, url_match = None, re.search(r'(https?://\S+\.(?:png|jpg|jpeg|gif))$', message)
        if url_match:
            gif_url = url_match.group(0)
            message = message[:url_match.start()].strip()
        announce_embed = discord.Embed(title="📢 Official Announcement from MehdiBOT", description=f"## {message}",
            color=0x5865F2, timestamp=ctx.message.created_at)
        if gif_url: announce_embed.set_image(url=gif_url)
        announce_embed.set_footer(text=f"From your developer, {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        sent_user_ids, success_count, failure_count = set(), 0, 0
        progress_message = await ctx.reply(f"📢 Starting global announcement... This may take a while.")
        for member in self.bot.get_all_members():
            if member.bot or member.id in sent_user_ids: continue
            try:
                await member.send(embed=announce_embed)
                success_count += 1
                sent_user_ids.add(member.id)
                await asyncio.sleep(0.1) 
            except (discord.Forbidden, discord.HTTPException): failure_count += 1
        await progress_message.edit(content=f"📢 Announcement complete!\n✅ **Successfully sent to:** {success_count} users\n❌ **Failed to send to:** {failure_count} users")

async def setup(bot: commands.Bot):
    await bot.add_cog(Owner(bot))

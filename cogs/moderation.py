# cogs/moderation.py
import discord
from discord.ext import commands

class Moderation(commands.Cog):
    """Commands for server moderation."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="kick", help="Kicks a user from the server.")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided."):
        if member == ctx.author:
            return await ctx.reply("❌ You cannot kick yourself!")
        
        await member.kick(reason=reason)
        await ctx.reply(f"✅ **{member}** has been kicked. Reason: `{reason}`")

    @commands.command(name="ban", help="Bans a user from the server.")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided."):
        if member == ctx.author:
            return await ctx.reply("❌ You cannot ban yourself!")
        
        await member.ban(reason=reason)
        await ctx.reply(f"✅ **{member}** has been banned. Reason: `{reason}`")

    # --- NEW UNBAN COMMAND ---
    @commands.command(name="unban", help="Unbans a user by their ID.")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int):
        """Unbans a user from the server by their User ID."""
        try:
            # Fetch the user object from the ID
            user = await self.bot.fetch_user(user_id)
        except discord.NotFound:
            return await ctx.reply("❌ No user found with that ID.")
        
        try:
            # Try to unban the user
            await ctx.guild.unban(user, reason=f"Unbanned by {ctx.author.name}")
            await ctx.reply(f"✅ Successfully unbanned **{user.name}**.")
        except discord.NotFound:
            # This error is raised if the user is not in the server's ban list
            await ctx.reply(f"❌ **{user.name}** is not banned from this server.")
        except discord.Forbidden:
            await ctx.reply("❌ I don't have the permissions to unban users.")


    @commands.command(name="mute", help="Mutes a user in all text channels.")
    @commands.has_permissions(manage_roles=True, manage_channels=True)
    @commands.bot_has_permissions(manage_roles=True, manage_channels=True)
    async def mute(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided."):
        """
        Mutes a member by applying a permission overwrite in every text channel.
        This is more reliable than using roles alone.
        """
        if member == ctx.author:
            return await ctx.reply("❌ You cannot mute yourself!")
        if member.guild_permissions.administrator:
            return await ctx.reply("❌ You cannot mute an administrator.")

        progress_message = await ctx.reply(f"Muting **{member.name}** in all text channels... This may take a moment.")
        
        muted_channels = 0
        for channel in ctx.guild.text_channels:
            try:
                await channel.set_permissions(member, send_messages=False, reason=f"Mute by {ctx.author.name}: {reason}")
                muted_channels += 1
            except discord.Forbidden:
                print(f"Could not mute {member.name} in {channel.name} - No permission.")
            except Exception as e:
                print(f"Failed to mute {member.name} in {channel.name}: {e}")

        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not muted_role:
             muted_role = await ctx.guild.create_role(name="Muted", reason="Visual indicator for muted users")
        
        if muted_role not in member.roles:
            await member.add_roles(muted_role, reason=reason)

        await progress_message.edit(content=f"✅ **{member.mention}** has been muted in **{muted_channels}** text channels. Reason: `{reason}`")

    @commands.command(name="unmute", help="Unmutes a previously muted user.")
    @commands.has_permissions(manage_roles=True, manage_channels=True)
    @commands.bot_has_permissions(manage_roles=True, manage_channels=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member):
        """Removes the mute overwrite for a member in all text channels."""
        progress_message = await ctx.reply(f"Unmuting **{member.name}**... This may take a moment.")

        unmuted_channels = 0
        for channel in ctx.guild.text_channels:
            if channel.overwrites_for(member).send_messages is False:
                try:
                    await channel.set_permissions(member, send_messages=None, reason=f"Unmute by {ctx.author.name}")
                    unmuted_channels += 1
                except discord.Forbidden:
                    print(f"Could not unmute {member.name} in {channel.name} - No permission.")
                except Exception as e:
                    print(f"Failed to unmute {member.name} in {channel.name}: {e}")
        
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if muted_role and muted_role in member.roles:
            await member.remove_roles(muted_role)

        await progress_message.edit(content=f"✅ **{member.mention}** has been unmuted in **{unmuted_channels}** channels.")

    @commands.command(name="clear", aliases=["purge"], help="Deletes a specified number of messages.")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, amount: int):
        if amount <= 0:
            return await ctx.reply("❌ Please provide a positive number of messages to delete.")
        
        deleted = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f"✅ Deleted **{len(deleted) - 1}** messages.", delete_after=5)

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))

# cogs/gaming.py
import discord
from discord.ext import commands
import aiohttp
from datetime import datetime
import base64
import io

class Gaming(commands.Cog):
    """Commands related to gaming and game server statuses."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="mcstatus", help="Shows the status of a Minecraft server.")
    async def mcstatus(self, ctx: commands.Context, server_ip: str):
        """Fetches and displays the status of a Java or Bedrock Minecraft server."""
        
        message = await ctx.reply(f"Pinging Minecraft server `{server_ip}`...")
        api_url = f"https://api.mcsrvstat.us/2/{server_ip}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status != 200:
                        return await message.edit(content="❌ Could not connect to the status API.")
                    data = await response.json()

                    if not data.get('online', False):
                        embed = discord.Embed(title=f"Minecraft Server Status: {server_ip}", description="**Server is currently offline.**", color=discord.Color.red())
                        return await message.edit(content=None, embed=embed)

                    embed = discord.Embed(title=f"Minecraft Server: {data.get('hostname', server_ip)}", color=discord.Color.green())
                    embed.add_field(name="Status", value="🟢 Online", inline=True)
                    embed.add_field(name="Players", value=f"{data['players']['online']} / {data['players']['max']}", inline=True)
                    embed.add_field(name="Version", value=data.get('version', 'N/A'), inline=True)
                    
                    motd = "\n".join(data.get('motd', {}).get('clean', []))
                    if motd:
                        embed.add_field(name="MOTD", value=f"```\n{motd}\n```", inline=False)
                        
                    icon_data = data.get('icon')
                    if icon_data:
                        try:
                            image_data = base64.b64decode(icon_data.split(',')[-1])
                            icon_file = discord.File(fp=io.BytesIO(image_data), filename="icon.png")
                            embed.set_thumbnail(url="attachment://icon.png")
                            await message.edit(content=None, embed=embed, attachments=[icon_file])
                        except Exception as e:
                            print(f"Failed to process server icon: {e}")
                            await message.edit(content=None, embed=embed)
                    else:
                        await message.edit(content=None, embed=embed)

        except Exception as e:
            await message.edit(content=f"❌ An error occurred while checking the server: {e}")

    @commands.command(name="rbxstatus", help="Shows the status of a Roblox game.")
    async def rbxstatus(self, ctx: commands.Context, place_id: int):
        """Fetches game status using multiple, more reliable Roblox API endpoints."""
        message = await ctx.reply(f"Fetching Roblox game data for Place ID `{place_id}`...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Step 1: Get Universe ID
                universe_api_url = f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
                async with session.get(universe_api_url) as resp:
                    if resp.status != 200:
                        return await message.edit(content=f"❌ Could not find a universe for Place ID `{place_id}`.")
                    universe_data = await resp.json()
                    universe_id = universe_data.get('universeId')

                # Step 2: Get main game details
                games_api_url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"
                async with session.get(games_api_url) as resp:
                    game_details_data = await resp.json()
                    game_data = game_details_data['data'][0]
                
                # --- THIS IS THE FIX (PART 1) ---
                # Step 3: Get likes (upVotes) from a different API endpoint
                votes_api_url = f"https://games.roblox.com/v1/games/votes?universeIds={universe_id}"
                likes = 0
                async with session.get(votes_api_url) as resp:
                    if resp.status == 200:
                        votes_data = await resp.json()
                        if votes_data.get('data') and votes_data['data'][0]:
                            likes = votes_data['data'][0].get('upVotes', 0)

                # Step 4: Get game thumbnail
                thumb_api_url = f"https://thumbnails.roblox.com/v1/games/icons?universeIds={universe_id}&size=256x256&format=Png&isCircular=false"
                thumb_url = None
                async with session.get(thumb_api_url) as resp:
                    if resp.status == 200:
                        thumb_data = await resp.json()
                        if thumb_data.get('data') and thumb_data['data'][0]:
                            thumb_url = thumb_data['data'][0].get('imageUrl')

                # Step 5: Build the embed
                embed = discord.Embed(
                    title=f"Roblox Game: {game_data.get('name', 'Unknown')}",
                    url=f"https://www.roblox.com/games/{place_id}",
                    description=(game_data['description'][:250] + '...' if game_data.get('description') and len(game_data['description']) > 250 else game_data.get('description', '')),
                    color=0x00A2FF # Roblox Blue
                )
                if thumb_url:
                    embed.set_thumbnail(url=thumb_url)

                embed.add_field(name="Players", value=f"{game_data.get('playing', 0):,}", inline=True)
                embed.add_field(name="Visits", value=f"{game_data.get('visits', 0):,}", inline=True)
                embed.add_field(name="Likes", value=f"{likes:,}", inline=True) # Use the new 'likes' variable
                embed.add_field(name="Favorites", value=f"{game_data.get('favoritedCount', 0):,}", inline=True)
                embed.add_field(name="Creator", value=game_data.get('creator', {}).get('name', 'Unknown'), inline=True)
                
                # --- THIS IS THE FIX (PART 2) ---
                now = discord.utils.utcnow()
                created_date = datetime.fromisoformat(game_data.get('created'))
                created_days = (now - created_date).days
                embed.add_field(name="Created", value=f"<t:{int(created_date.timestamp())}:D>\n({created_days} days ago)", inline=True)
                
                await message.edit(content=None, embed=embed)

        except Exception as e:
            await message.edit(content=f"❌ An unexpected error occurred: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Gaming(bot))

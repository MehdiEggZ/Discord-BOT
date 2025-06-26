# cogs/music.py
import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
import datetime
import random

# --- yt-dlp and FFmpeg Options ---
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

# Simplified, stable FFmpeg options
ffmpeg_options = {
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('webpage_url')
        self.duration_seconds = data.get('duration')
        self.thumbnail = data.get('thumbnail')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url']
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

    @property
    def duration(self) -> str:
        if self.duration_seconds:
            td = datetime.timedelta(seconds=self.duration_seconds)
            minutes, seconds = divmod(td.seconds, 60)
            hours, minutes = divmod(minutes, 60)
            return f"{hours:02}:{minutes:02}:{seconds:02}" if td.days > 0 or hours > 0 else f"{minutes:02}:{seconds:02}"
        return "N/A"

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild_states = {}

    def get_state(self, guild_id: int):
        if guild_id not in self.guild_states:
            self.guild_states[guild_id] = {
                "queue": [], "now_playing": None, "random_history": [],
                "loop": False, "previous_song": None
            }
        return self.guild_states[guild_id]

    async def play_from_data(self, ctx: commands.Context, song_data: dict):
        """A robust helper function to play a song from its data dictionary."""
        state = self.get_state(ctx.guild.id)
        try:
            player = await YTDLSource.from_url(song_data["url"], loop=self.bot.loop)
            state["now_playing"] = player
            ctx.voice_client.play(player, after=lambda e: self.play_next_song(ctx))
            embed = discord.Embed(title="🎶 Now Playing", color=discord.Color.green(), description=f"**[{player.title}]({player.url})**")
            embed.set_thumbnail(url=player.thumbnail).set_footer(text=f"Duration: {player.duration}")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error playing `{song_data['title']}`: {e}")
            self.play_next_song(ctx) # Try next song on error

    def play_next_song(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        state["previous_song"] = state.get("now_playing")

        if state["loop"] and state["previous_song"]:
            state["now_playing"] = state["previous_song"]
            asyncio.run_coroutine_threadsafe(self.replay_source(ctx, state["now_playing"]), self.bot.loop)
            return

        state["now_playing"] = None
        if not state["queue"]:
            return

        next_song_data = state["queue"].pop(0)
        asyncio.run_coroutine_threadsafe(self.play_from_data(ctx, next_song_data), self.bot.loop)

    async def replay_source(self, ctx: commands.Context, song: YTDLSource):
        try:
            new_source = await YTDLSource.from_url(song.url, loop=self.bot.loop)
            if ctx.voice_client.source:
                new_source.volume = ctx.voice_client.source.volume
            ctx.voice_client.play(new_source, after=lambda e: self.play_next_song(ctx))
        except Exception as e:
            await ctx.send(f"❌ Error replaying song: {e}")

    async def get_player(self, ctx: commands.Context):
        if not ctx.author.voice:
            await ctx.reply("❌ You must be in a voice channel to use music commands.")
            return None
        if ctx.voice_client is None: await ctx.author.voice.channel.connect()
        return ctx.voice_client

    @commands.command(name="play", aliases=['p'], help="Plays a song directly from YouTube.")
    async def play(self, ctx: commands.Context, *, query: str):
        vc = await self.get_player(ctx)
        if not vc: return
        state, message = self.get_state(ctx.guild.id), None
        if ctx.invoked_with in ['play', 'p']: message = await ctx.reply(f"🔎 Searching for `{query}`...")
        try:
            player = await YTDLSource.from_url(query, loop=self.bot.loop)
            # Store serializable data, not the object itself
            song_data = {"title": player.title, "url": player.url}
        except Exception as e:
            if message: await message.edit(content=f"❌ An error occurred: {e}")
            else: await ctx.reply(f"❌ An error occurred: {e}")
            return
        if message: await message.delete()
        if vc.is_playing() or state["now_playing"]:
            state["queue"].append(song_data)
            await ctx.reply(f"✅ **Added to queue:** {player.title}")
        else:
            await self.play_from_data(ctx, song_data)

    # --- FIXED PREVIOUS COMMAND ---
    @commands.command(name="previous", aliases=['prev'], help="Plays the previous song again.")
    async def previous(self, ctx: commands.Context):
        vc = await self.get_player(ctx)
        if not vc: return

        state = self.get_state(ctx.guild.id)
        previous_song_player = state.get("previous_song")

        if not previous_song_player:
            return await ctx.reply("❌ There is no previous song in history.")
        
        # Create serializable data for the songs
        previous_song_data = {"title": previous_song_player.title, "url": previous_song_player.url}
        
        # Add the currently playing song back to the start of the queue
        now_playing_player = state.get("now_playing")
        if now_playing_player:
            now_playing_data = {"title": now_playing_player.title, "url": now_playing_player.url}
            state["queue"].insert(0, now_playing_data)

        # Add the previous song to the very front so it plays next
        state["queue"].insert(0, previous_song_data)

        # Skip the current track to immediately trigger the next one
        if vc.is_playing() or vc.is_paused():
            vc.stop()
        else:
            # If nothing is playing, just start the queue
            self.play_next_song(ctx)
        
        await ctx.reply("⏮️ Playing the previous song.")
        
    # ... (rest of the commands are unchanged)
    @commands.command(name="random", help="Plays a random popular song.")
    async def random(self, ctx: commands.Context):
        vc = await self.get_player(ctx)
        if not vc: return
        state = self.get_state(ctx.guild.id)
        message = await ctx.reply("🎶 Finding a new random song...")
        search_queries = ["Top Global Hits Today", "Billboard Hot 100", "Viral Hits Playlist", "Most Streamed Songs Globally", "Today's Top Hits"]
        random_query = random.choice(search_queries)
        try:
            await message.edit(content=f"🔎 Searching for tracks related to: **{random_query}**")
            with yt_dlp.YoutubeDL({'extract_flat': 'in_playlist', 'quiet': True, 'default_search': 'ytsearch10'}) as ydl:
                search_results = await self.bot.loop.run_in_executor(None, lambda: ydl.extract_info(random_query, download=False))
            if not search_results or not search_results.get('entries'):
                return await message.edit(content="❌ Could not find any songs for the random search.")
            chosen_song_info = None
            for song_info in random.sample(search_results['entries'], len(search_results['entries'])):
                if song_info and song_info.get('id') not in state['random_history']:
                    chosen_song_info = song_info
                    break
            if chosen_song_info is None: chosen_song_info = random.choice(search_results['entries'])
            song_url = chosen_song_info.get('url')
            if not song_url: return await message.edit(content="❌ Found a random song, but could not get its URL.")
            state['random_history'].append(chosen_song_info.get('id'))
            if len(state['random_history']) > 20: state['random_history'].pop(0)
            await message.delete()
            await ctx.invoke(self.play, query=song_url)
        except Exception as e:
            await message.edit(content=f"❌ An error occurred while finding a random song: {e}")

    @commands.command(name="skip", aliases=['s'], help="Skips the current song.")
    async def skip(self, ctx: commands.Context):
        if not ctx.voice_client or not ctx.voice_client.is_playing(): return await ctx.reply("❌ I am not playing any music.")
        ctx.voice_client.stop()
        await ctx.reply("⏭️ Skipped song.")

    @commands.command(name="pause", help="Pauses the current song.")
    async def pause(self, ctx: commands.Context):
        vc = ctx.voice_client
        if not vc or not vc.is_playing(): return await ctx.reply("❌ I am not currently playing anything.")
        if vc.is_paused(): return await ctx.reply("The music is already paused.")
        vc.pause()
        await ctx.reply("⏸️ Paused the music.")

    @commands.command(name="resume", help="Resumes the paused music.")
    async def resume(self, ctx: commands.Context):
        vc = ctx.voice_client
        if not vc or not vc.is_paused(): return await ctx.reply("❌ The music is not paused.")
        vc.resume()
        await ctx.reply("▶️ Resumed the music.")

    @commands.command(name="replay", help="Replays the current song from the beginning.")
    async def replay(self, ctx: commands.Context):
        vc = ctx.voice_client
        if not vc or not (vc.is_playing() or vc.is_paused()):
            return await ctx.reply("❌ I'm not playing anything right now.")
        state = self.get_state(ctx.guild.id)
        current_song = state.get("now_playing")
        if not current_song:
            return await ctx.reply("❌ There's no song to replay.")
        await self.replay_source(ctx, current_song)
        await ctx.reply("🔄 Replaying the current song.")

    @commands.command(name="loop", help="Toggles looping for the current song.")
    async def loop(self, ctx: commands.Context):
        vc = ctx.voice_client
        if not vc or not (vc.is_playing() or vc.is_paused()):
            return await ctx.reply("❌ I'm not playing anything right now.")
        state = self.get_state(ctx.guild.id)
        state["loop"] = not state["loop"]
        await ctx.reply(f"🔁 Looping is now **{'enabled' if state['loop'] else 'disabled'}** for the current song.")

    @commands.command(name="unloop", help="Disables looping for the current song.")
    async def unloop(self, ctx: commands.Context):
        vc = ctx.voice_client
        if not vc or not (vc.is_playing() or vc.is_paused()):
            return await ctx.reply("❌ I'm not playing anything right now.")
        state = self.get_state(ctx.guild.id)
        if not state["loop"]:
            return await ctx.reply("🔁 Looping is already **disabled**.")
        state["loop"] = False
        await ctx.reply("🔁 Looping has been **disabled**.")

    @commands.command(name="queue", aliases=['q'], help="Displays the song queue.")
    async def queue(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        now_playing_player = state.get("now_playing")
        embed = discord.Embed(title="📜 Song Queue", color=discord.Color.purple())
        embed.description = f"**Now Playing:**\n[{now_playing_player.title}]({now_playing_player.url}) `({now_playing_player.duration})`" if now_playing_player else "Nothing is currently playing."
        if state['queue']:
            song_list = "\n".join(f"**{i}.** {s['title']}" for i, s in enumerate(state['queue'][:10], 1))
            embed.add_field(name="Up Next", value=song_list, inline=False)
        if len(state['queue']) > 10: embed.set_footer(text=f"And {len(state['queue']) - 10} more...")
        await ctx.reply(embed=embed)

    @commands.command(name="nowplaying", aliases=['np'], help="Shows the currently playing song.")
    async def nowplaying(self, ctx: commands.Context):
        now_playing = self.get_state(ctx.guild.id)["now_playing"]
        if not now_playing: return await ctx.reply("Nothing is currently playing.")
        embed = discord.Embed(title="🎶 Now Playing", color=discord.Color.green(), description=f"**[{now_playing.title}]({now_playing.url})**")
        embed.set_thumbnail(url=now_playing.thumbnail).set_footer(text=f"Duration: {now_playing.duration}")
        await ctx.reply(embed=embed)

    @commands.command(name="volume", help="Changes the player's volume (0-200).")
    async def volume(self, ctx: commands.Context, value: int):
        if not ctx.voice_client or not ctx.voice_client.source: return await ctx.reply("I am not currently playing anything.")
        if not 0 <= value <= 200: return await ctx.reply("❌ Please enter a value between 0 and 200.")
        ctx.voice_client.source.volume = value / 100
        await ctx.reply(f"✅ Set volume to **{value}%**")

    @commands.command(name="stop", aliases=['leave', 'dc'], help="Stops music and disconnects.")
    async def stop(self, ctx: commands.Context):
        if not ctx.voice_client: return await ctx.reply("I am not in a voice channel.")
        state = self.get_state(ctx.guild.id)
        state.clear()
        self.guild_states.pop(ctx.guild.id, None)
        await ctx.voice_client.disconnect()
        await ctx.reply("👋 Disconnected and cleared queue.")

async def setup(bot: commands.Bot): await bot.add_cog(Music(bot))

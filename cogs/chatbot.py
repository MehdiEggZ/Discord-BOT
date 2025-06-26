# cogs/chatbot.py
import discord
from discord.ext import commands
from config import GEMINI_API_KEY
import google.generativeai as genai
import io
import json # New import for file handling
import os   # New import for file path checking

# --- NEW: History File Management ---
HISTORY_FILE = "conversation_history.json"

def load_history():
    """Loads the conversation history from a JSON file."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            try:
                # JSON keys must be strings, so convert channel IDs back to integers on load
                return {int(k): v for k, v in json.load(f).items()}
            except (json.JSONDecodeError, ValueError):
                return {} # Return empty dictionary if file is corrupted or empty
    return {}

def save_history(history_data):
    """Saves the entire conversation history to a JSON file."""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history_data, f, indent=4)


class Chatbot(commands.Cog):
    """
    A conversational AI agent powered by Google Gemini with persistent conversation memory.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # --- UPDATED: Load history from file on startup ---
        self.conversation_histories = load_history()
        
        # Configure the Gemini API client
        try:
            if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
                genai.configure(api_key=GEMINI_API_KEY)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                print("Chatbot cog configured successfully with Gemini.")
            else:
                print("Gemini API key not found. Chatbot features will be disabled.")
                self.model = None
        except Exception as e:
            print(f"Failed to configure Gemini text model: {e}")
            self.model = None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Listens for messages, maintains a conversation history, and responds using Gemini.
        """
        if message.author.bot:
            return

        is_ping = self.bot.user.mentioned_in(message)
        is_reply_to_bot = False
        if message.reference and message.reference.resolved and message.reference.resolved.author == self.bot.user:
            is_reply_to_bot = True
        contains_name = "mehdi bot" in message.content.lower()

        if not is_ping and not is_reply_to_bot and not contains_name:
            return

        if not self.model:
            print("Chatbot listener triggered, but Gemini model is not configured.")
            return

        if is_ping:
            prompt = message.content.replace(f'<@!{self.bot.user.id}>', '').replace(f'<@{self.bot.user.id}>', '').strip()
        else:
            prompt = message.content.strip()
        
        if not prompt:
            return await message.reply("You mentioned me! How can I help you today?")

        channel_id = message.channel.id
        history = self.conversation_histories.setdefault(channel_id, [])

        async with message.channel.typing():
            try:
                full_prompt = history + [{'role': 'user', 'parts': [prompt]}]
                response = await self.model.generate_content_async(full_prompt)
                
                history.append({'role': 'user', 'parts': [prompt]})
                history.append({'role': 'model', 'parts': [response.text]})

                if len(history) > 10:
                    self.conversation_histories[channel_id] = history[-10:]

                # --- NEW: Save the updated history to the file ---
                save_history(self.conversation_histories)

                if len(response.text) > 2000:
                    await message.reply("The response was too long, so I've sent it as a file.", file=discord.File(io.StringIO(response.text), "response.txt"))
                else:
                    await message.reply(response.text)
            except Exception as e:
                await message.reply(f"❌ An error occurred with the Gemini API: `{e}`")

async def setup(bot: commands.Bot):
    """Adds the cog to the bot."""
    await bot.add_cog(Chatbot(bot))

# cogs/translate.py
import discord
from discord.ext import commands
from googletrans import Translator, LANGUAGES
from config import PREFIX

class Translate(commands.Cog):
    """Commands for translating text."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.translator = Translator()

    @commands.command(name="translate", help="Translates text to a specified language.")
    async def translate(self, ctx: commands.Context, language: str, *, text: str):
        language = language.lower()
        if language not in LANGUAGES and language not in LANGUAGES.values():
            return await ctx.reply(f"❌ Invalid language. See `{PREFIX}languages`.")
        try:
            translation = self.translator.translate(text, dest=language)
            src_lang_name = LANGUAGES.get(translation.src.lower(), "Unknown").title()
            dest_lang_name = LANGUAGES.get(translation.dest.lower(), "Unknown").title()
            embed = discord.Embed(title="🌐 Translation Successful", color=discord.Color.blue())
            embed.add_field(name=f"Original Text ({src_lang_name})", value=f"```\n{text}\n```", inline=False)
            embed.add_field(name=f"Translated Text ({dest_lang_name})", value=f"```\n{translation.text}\n```", inline=False)
            embed.set_footer(text=f"Translated for {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"An error occurred during translation: {e}")

    @commands.command(name="languages", aliases=["langs"], help="Lists supported languages for translation.")
    async def languages(self, ctx: commands.Context):
        common_langs = {'english': 'en', 'spanish': 'es', 'french': 'fr', 'german': 'de', 'japanese': 'ja', 'korean': 'ko', 'chinese (simplified)': 'zh-cn', 'arabic': 'ar', 'russian': 'ru', 'portuguese': 'pt', 'italian': 'it', 'hindi': 'hi'}
        description = "Here are some common languages you can use:\n\n"
        for lang, code in common_langs.items():
            description += f"**{lang.title()}**: `{code}`\n"
        embed = discord.Embed(title="Supported Languages", description=description, color=discord.Color.dark_green())
        embed.set_footer(text=f"Use either the full name or the code in the {PREFIX}translate command.")
        await ctx.reply(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Translate(bot))   
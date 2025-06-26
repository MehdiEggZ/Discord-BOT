# cogs/twentyquestions.py
import discord
from discord.ext import commands
import google.generativeai as genai
from config import GEMINI_API_KEY
import asyncio

# --- Translations for UI elements and messages ---
TRANSLATIONS = {
    "en": {
        "yes": "Yes",
        "no": "No",
        "maybe": "Maybe / Sometimes",
        "i_win": "I Win! (Bot Guesses)",
        "start_message": "🤔 I'm ready! Think of an object, and I will try to guess it. I'll ask my first question in a moment...",
        "timeout_message": "Game timed out due to inactivity.",
        "stop_message": "Game over! Thanks for playing.",
        "guess_message": "My final guess is... **{guess}**! Was I right, {mention}?",
        "not_your_game": "This is not your game!",
        "already_running": "A game is already in progress in this channel! Use `.stopq` to end it.",
        "no_game_to_stop": "There is no game in progress to stop.",
        "permission_denied_stop": "Only {mention} or a moderator can stop this game."
    },
    "ar": {
        "yes": "نعم",
        "no": "لا",
        "maybe": "ربما / أحيانا",
        "i_win": "لقد فزت! (تخمين البوت)",
        "start_message": "🤔 أنا مستعد! فكر في شيء وسأحاول تخمينه. سأطرح سؤالي الأول بعد لحظات...",
        "timeout_message": "انتهت اللعبة بسبب عدم النشاط.",
        "stop_message": "انتهت اللعبة! شكرا للعب.",
        "guess_message": "تخميني الأخير هو... **{guess}**! هل كنت على حق يا {mention}؟",
        "not_your_game": "هذه ليست لعبتك!",
        "already_running": "هناك لعبة جارية بالفعل في هذه القناة! استخدم `.stopq` لإنهائها.",
        "no_game_to_stop": "لا توجد لعبة جارية لإيقافها.",
        "permission_denied_stop": "فقط {mention} أو مشرف يمكنه إيقاف هذه اللعبة."
    }
}

# --- Game View (Buttons) ---
class TwentyQuestionsView(discord.ui.View):
    def __init__(self, author, language="en"):
        super().__init__(timeout=300.0)
        self.author, self.value = author, None
        lang_ui = TRANSLATIONS.get(language, TRANSLATIONS["en"])
        self.children[0].label, self.children[1].label, self.children[2].label, self.children[3].label = lang_ui["yes"], lang_ui["no"], lang_ui["maybe"], lang_ui["i_win"]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            lang_code = "ar" if "نعم" in self.children[0].label else "en"
            await interaction.response.send_message(TRANSLATIONS[lang_code]["not_your_game"], ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "Yes"; self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "No"; self.stop()
    
    @discord.ui.button(label="Maybe / Sometimes", style=discord.ButtonStyle.blurple)
    async def maybe(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "Maybe or sometimes"; self.stop()

    @discord.ui.button(label="I Win! (Bot Guesses)", style=discord.ButtonStyle.secondary, emoji="🏆")
    async def i_win(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "I Win"; self.stop()

class TwentyQuestions(commands.Cog):
    """A 20 Questions game powered by Gemini AI."""
    def __init__(self, bot: commands.Bot):
        self.bot, self.games = bot, {}
        try:
            if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
                genai.configure(api_key=GEMINI_API_KEY)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            else: self.model = None
        except Exception as e:
            print(f"Failed to configure Gemini for 20Q: {e}"); self.model = None

    @commands.command(name="20q", help="Starts a game of 20 Questions.")
    async def start_20q(self, ctx: commands.Context, *args):
        """Starts an interactive game, parsing arguments for question count and language."""
        if not self.model:
            return await ctx.reply("❌ The Gemini AI service is not configured.")
        if ctx.channel.id in self.games:
            # Determine language for error message if possible
            lang_code_for_error = "en"
            for arg in args:
                if arg.lower() in TRANSLATIONS: lang_code_for_error = arg.lower()
            return await ctx.reply(TRANSLATIONS[lang_code_for_error]["already_running"])

        # Default values
        questions = 20
        lang_code = "en"
        
        # Parse arguments
        for arg in args:
            if arg.isdigit():
                q = int(arg)
                if 3 <= q <= 30:
                    questions = q
                else:
                    return await ctx.reply("❌ Please choose a number of questions between 3 and 30.")
            elif arg.lower() in TRANSLATIONS:
                lang_code = arg.lower()
            else:
                return await ctx.reply(f"❌ Invalid argument `{arg}`. Please provide a number (3-30) or a language (`en`, `ar`).")

        language_map = {"en": "English", "ar": "Arabic"}
        language_name = language_map.get(lang_code, "English")
        
        initial_prompt = (
            f"Let's play a game where you try to guess an object I'm thinking of. You have {questions} questions. "
            f"You MUST ask all questions and make all guesses strictly in the {language_name} language. "
            f"Your response MUST ONLY contain the question itself, with no other text, translation, or transliteration. "
            f"Start with your first question now."
        )

        self.games[ctx.channel.id] = {
            "author": ctx.author, "questions_asked": 0, "max_questions": questions,
            "language": lang_code, "history": [{'role': 'user', 'parts': [initial_prompt]}]
        }
        
        await ctx.reply(TRANSLATIONS[lang_code]["start_message"])
        await asyncio.sleep(2)
        await self.ask_next_question(ctx)

    async def ask_next_question(self, ctx: commands.Context):
        game_state = self.games.get(ctx.channel.id)
        if not game_state: return

        lang_code = game_state["language"]
        lang_ui = TRANSLATIONS.get(lang_code, TRANSLATIONS["en"])

        if game_state["questions_asked"] >= game_state["max_questions"]:
            return await self.end_game(ctx, with_guess=True)

        async with ctx.typing():
            try:
                response = await self.model.generate_content_async(game_state["history"])
                question = response.text.strip()
                game_state["history"].append({'role': 'model', 'parts': [question]})
                game_state["questions_asked"] += 1
                
                view = TwentyQuestionsView(ctx.author, lang_code)
                embed = discord.Embed(
                    title=f"Question {game_state['questions_asked']}/{game_state['max_questions']}",
                    description=question, color=discord.Color.blue()
                ).set_footer(text=f"Thinking of an object? Answer for {ctx.author.display_name}")
                
                message = await ctx.send(embed=embed, view=view)
                await view.wait()
                
                await message.edit(view=None)
                
                if view.value == "I Win": await self.end_game(ctx, with_guess=True)
                elif view.value:
                    game_state["history"].append({'role': 'user', 'parts': [f"The answer is: {view.value}"]})
                    await self.ask_next_question(ctx)
                else:
                    await ctx.send(lang_ui["timeout_message"])
                    if ctx.channel.id in self.games: del self.games[ctx.channel.id]

            except Exception as e:
                await ctx.send(f"❌ An error occurred with the Gemini API: {e}")
                if ctx.channel.id in self.games: del self.games[ctx.channel.id]

    async def end_game(self, ctx: commands.Context, with_guess: bool = False):
        game_state = self.games.get(ctx.channel.id)
        if not game_state: return

        lang_code, lang_ui = game_state["language"], TRANSLATIONS.get(game_state["language"], TRANSLATIONS["en"])
        language_map = {"en": "English", "ar": "Arabic"}
        language_name = language_map.get(lang_code, "English")

        if with_guess:
            async with ctx.typing():
                final_prompt = (
                    f"Based on my answers, what is your best guess for what the object is? "
                    f"Your response MUST be strictly in {language_name} and contain ONLY the name of the object you are guessing, with no other text or translation."
                )
                game_state["history"].append({'role': 'user', 'parts': [final_prompt]})
                response = await self.model.generate_content_async(game_state["history"])
                await ctx.send(lang_ui["guess_message"].format(guess=response.text.strip(), mention=ctx.author.mention))
        else:
            await ctx.send(lang_ui["stop_message"])

        if ctx.channel.id in self.games: del self.games[ctx.channel.id]

    @commands.command(name="stopq", help="Stops the current game of 20 Questions.")
    async def stop_20q(self, ctx: commands.Context):
        if ctx.channel.id not in self.games:
            return await ctx.reply("There is no game in progress to stop.")
        
        game_state = self.games[ctx.channel.id]
        game_author, lang_code = game_state["author"], game_state["language"]
        lang_ui = TRANSLATIONS.get(lang_code, TRANSLATIONS["en"])

        if ctx.author != game_author and not ctx.author.guild_permissions.manage_messages:
            return await ctx.reply(lang_ui["permission_denied_stop"].format(mention=game_author.mention))
            
        await self.end_game(ctx, with_guess=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(TwentyQuestions(bot))

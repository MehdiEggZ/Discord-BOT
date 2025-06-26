# cogs/converters.py
import discord
from discord.ext import commands
import aiohttp
import re # For cleaning the math expression

class Converters(commands.Cog):
    """A collection of useful calculators and converters."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Conversion factors relative to a base unit (e.g., meters, grams)
        self.units = {
            # Length
            "km": 1000, "m": 1, "cm": 0.01, "mm": 0.001,
            "mi": 1609.34, "yd": 0.9144, "ft": 0.3048, "in": 0.0254,
            # Weight
            "kg": 1000, "g": 1, "mg": 0.001,
            "lb": 453.592, "oz": 28.3495
        }

    @commands.command(name="calculate", aliases=['calc', 'math'], help="Calculates a mathematical expression.")
    async def calculate(self, ctx: commands.Context, *, expression: str):
        """A safe calculator for basic arithmetic."""
        try:
            # Remove any characters that are not numbers, operators, or parentheses
            clean_expression = re.sub(r'[^0-9\.\+\-\*\/\(\)\^ ]', '', expression)
            clean_expression = clean_expression.replace('^', '**') # Replace ^ with Python's power operator
            
            # This is a safer way to evaluate mathematical expressions from users.
            # It provides an empty dictionary for globals and locals, which prevents
            # the execution of malicious code.
            result = eval(clean_expression, {"__builtins__": {}}, {}) 
            
            embed = discord.Embed(title="🧮 Calculator", color=discord.Color.blue())
            embed.add_field(name="Expression", value=f"```\n{expression}\n```", inline=False)
            embed.add_field(name="Result", value=f"```\n{result}\n```", inline=False)
            await ctx.reply(embed=embed)
        except (SyntaxError, ZeroDivisionError, Exception) as e:
            await ctx.reply(f"❌ Invalid mathematical expression. Please check your input. Error: `{e}`")

    @commands.command(name="convert", help="Converts between different units.")
    async def convert(self, ctx: commands.Context, amount: float, from_unit: str, to_unit: str):
        """Converts values between common units (length, weight, temp)."""
        from_unit, to_unit = from_unit.lower(), to_unit.lower()

        # Handle temperature separately because it's not a simple multiplication
        if from_unit in ['c', 'f', 'k'] and to_unit in ['c', 'f', 'k']:
            # This is a complex feature to add, so for now, we'll keep it simple.
            return await ctx.reply("Temperature conversion is coming soon!")

        if from_unit not in self.units or to_unit not in self.units:
            return await ctx.reply(f"❌ Unsupported unit. Please use common length or weight units.")

        # Convert the input amount to the base unit (meters or grams)
        base_value = amount * self.units[from_unit]
        # Convert from the base unit to the target unit
        result = base_value / self.units[to_unit]
        
        embed = discord.Embed(title="📏 Unit Conversion", color=discord.Color.green())
        embed.add_field(name="From", value=f"`{amount} {from_unit}`", inline=True)
        embed.add_field(name="To", value=f"`{result:.2f} {to_unit}`", inline=True)
        await ctx.reply(embed=embed)

    @commands.command(name="currency", help="Converts currencies using real-time rates.")
    async def currency(self, ctx: commands.Context, amount: float, from_currency: str, to_currency: str):
        """Converts between currencies using live exchange rates."""
        from_curr = from_currency.upper()
        to_curr = to_currency.upper()
        
        # Free API for exchange rates
        API_URL = f"https://open.er-api.com/v6/latest/{from_curr}"
        
        message = await ctx.reply(f"Fetching latest exchange rates for **{from_curr}**...")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_URL) as response:
                    if response.status != 200:
                        return await message.edit(content="❌ Could not fetch exchange rates. The API might be down or the currency code is invalid.")
                    
                    data = await response.json()
                    
                    if data.get("result") == "error":
                        return await message.edit(content=f"❌ API Error: `{data.get('error-type')}`")

                    rates = data.get("rates")
                    if to_curr not in rates:
                        return await message.edit(content=f"❌ The target currency `{to_curr}` is not valid.")

                    conversion_rate = rates[to_curr]
                    result = amount * conversion_rate
                    
                    embed = discord.Embed(title="💱 Currency Conversion", color=0xFFD700) # Gold
                    embed.description = f"`{amount:,.2f} {from_curr}` is equal to `{result:,.2f} {to_curr}`"
                    embed.set_footer(text=f"Rate: 1 {from_curr} = {conversion_rate} {to_curr}")
                    await message.edit(content=None, embed=embed)

        except Exception as e:
            await message.edit(content=f"❌ An unexpected error occurred: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Converters(bot))

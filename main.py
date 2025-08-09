# main.py
import os
import logging
from discord.ext import commands
import discord

# config
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
PALADIUM_API_KEY = os.getenv("PALADIUM_API_KEY")
GUILD_ID = 1402777306455478354

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

logging.basicConfig(level=logging.INFO)
bot = commands.Bot(command_prefix="!", intents=intents)

async def load_cogs():
    for cog in ("cogs.primes", "cogs.tickets"):
        try:
            await bot.load_extension(cog)
            logging.info(f"Loaded cog {cog}")
        except Exception as e:
            logging.exception(f"Failed loading cog {cog}: {e}")

@bot.event
async def on_ready():
    logging.info(f"Bot ready as {bot.user} (id: {bot.user.id})")
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    logging.info("Commands synced.")
    await load_cogs()

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        raise RuntimeError("Please set DISCORD_TOKEN as env var")
    bot.run(TOKEN)

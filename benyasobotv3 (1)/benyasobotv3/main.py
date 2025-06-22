import discord
from discord.ext import commands
import os
import asyncio
import threading
import keepalive  # keepalive.py dosyan

intents = discord.Intents.all()
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    application_id=1385314588018475221  # Discord Developer Portal’dan Client ID
)

intents = discord.Intents.default()
intents.voice_states = True

@bot.event
async def on_ready():
    print(f"{bot.user} olarak giriş yapıldı.")
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} komut senkronize edildi.")
    except Exception as e:
        print(f"Slash komut sync hatası: {e}")

async def load_all_cogs():
    for filename in os.listdir("./"):
        if filename.endswith(".py") and filename != "main.py":
            try:
                await bot.load_extension(filename[:-3])
                print(f"{filename} yüklendi.")
            except Exception as e:
                print(f"{filename} yüklenirken hata: {e}")

async def main():
    threading.Thread(target=keepalive.run, daemon=True).start()
    async with bot:
        await load_all_cogs()  # music.py dahil tüm .py dosyalarını yükler
        await bot.start("MTM4NTMxNDU4ODAxODQ3NTIyMQ.G9YR6l.UzkOGTnkU_r3n9dGIbYtLyRfjNlN2-DyNRXTp0")  # Token'ı buraya koy, kimseyle paylaşma!

if __name__ == "__main__":
    asyncio.run(main())
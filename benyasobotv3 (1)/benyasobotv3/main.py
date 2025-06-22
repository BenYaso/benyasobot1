import discord
from discord.ext import commands
import os
import threading
from flask import Flask
import asyncio

# --- Keep Alive kısmı ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.daemon = True
    t.start()

# --- Discord Bot kısmı ---
intents = discord.Intents.all()
intents.voice_states = True  # Ses durumu izleme izni

bot = commands.Bot(command_prefix="!", intents=intents, application_id=1385314588018475221)

async def load_all_cogs():
    # Eğer coglar cogs klasöründeyse:
    # cog_folder = "./cogs"
    # for filename in os.listdir(cog_folder):
    #     if filename.endswith(".py"):
    #         try:
    #             await bot.load_extension(f"cogs.{filename[:-3]}")
    #             print(f"cogs/{filename} yüklendi.")
    #         except Exception as e:
    #             print(f"cogs/{filename} yüklenirken hata: {e}")

    # Eğer coglar ana dizindeyse:
    for filename in os.listdir("."):
        if filename.endswith(".py") and filename not in ("main.py", "keep_alive.py"):
            try:
                await bot.load_extension(filename[:-3])
                print(f"{filename} yüklendi.")
            except Exception as e:
                print(f"{filename} yüklenirken hata: {e}")

@bot.event
async def on_ready():
    print(f"{bot.user} olarak giriş yapıldı.")
    try:
        synced = await bot.tree.sync()  # Global senkronizasyon
        print(f"{len(synced)} komut global olarak senkronize edildi.")
    except Exception as e:
        print(f"Slash komut sync hatası: {e}")

async def main():
    keep_alive()  # Keep alive web server başlatılır
    async with bot:
        await load_all_cogs()
        await bot.start(os.getenv("TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())

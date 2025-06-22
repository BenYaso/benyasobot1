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

intents = discord.Intents.all()
intents.voice_states = True  # Ses durumu izleme izni

bot = commands.Bot(command_prefix="!", intents=intents, application_id=1385314588018475221)

async def load_all_cogs():
    for filename in os.listdir("./cogs"):  # coglar klasördeyse bunu kullan
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"{filename} yüklendi.")
            except Exception as e:
                print(f"{filename} yüklenirken hata: {e}")

@bot.event
async def on_ready():
    print(f"{bot.user} olarak giriş yapıldı.")
    try:
        # Test sunucusuna komutları yükle
        test_guild = discord.Object(id=1385317817888411729)  
        synced = await bot.tree.sync(guild=test_guild)
        print(f"{len(synced)} komut test sunucusuna senkronize edildi.")
    except Exception as e:
        print(f"Slash komut sync hatası: {e}")

async def main():
    keep_alive()  # Keep alive web server başlatılır
    async with bot:
        await load_all_cogs()
        await bot.start(os.getenv("TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())

import discord
from discord.ext import commands
import os
import threading
from keep_alive import keep_alive  # keep_alive.py dosyan

intents = discord.Intents.all()
intents.voice_states = True  # Eğer ses ile ilgili özellikler lazım ise

bot = commands.Bot(command_prefix="!", intents=intents, application_id=1385314588018475221)

@bot.event
async def on_ready():
    print(f"{bot.user} olarak giriş yapıldı.")
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} komut senkronize edildi.")
    except Exception as e:
        print(f"Slash komut sync hatası: {e}")

async def load_all_cogs():
    for filename in os.listdir("./cogs"):  # cogs klasöründe ise
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"{filename} yüklendi.")
            except Exception as e:
                print(f"{filename} yüklenirken hata: {e}")

if __name__ == "__main__":
    # Keep alive server'ı thread içinde başlat
    threading.Thread(target=keep_alive, daemon=True).start()

    # Cogs yüklemesi için async fonksiyonu çağırmak gerek, ama bot.run bloklayıcı
    # En basit haliyle şu şekilde yapalım:

    async def start_bot():
        await load_all_cogs()
        print("Tüm cogs yüklendi, bot başlatılıyor...")

    # Async fonksiyonu çalıştırmak için:
    import asyncio
    asyncio.run(start_bot())

    # Ardından bot.run()'u çağır
    bot.run(os.getenv("TOKEN"))

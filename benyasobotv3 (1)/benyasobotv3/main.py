import discord
from discord.ext import commands
import os
import threading
from flask import Flask

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

@bot.event
async def on_ready():
    print(f"{bot.user} olarak giriş yapıldı.")

if __name__ == "__main__":
    keep_alive()  # Web server'ı başlat
    bot.run(os.getenv("TOKEN"))

import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Yt-dlp ayarları
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

ffmpeg_options = {
    'options': '-vn'
}

# Oynatma kuyruğu, kullanıcı sesi için basit dict
queues = {}

# Ses durumu ve kontrol için bir view (butonlar)
class MusicControls(discord.ui.View):
    def __init__(self, player, *, timeout=180):
        super().__init__(timeout=timeout)
        self.player = player
        self.paused = False

    @discord.ui.button(label="Durdur", style=discord.ButtonStyle.red)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.voice is None or interaction.user.voice.channel != self.player.voice.channel:
            await interaction.response.send_message("Sesli kanalda değilsin!", ephemeral=True)
            return
        self.player.voice.stop()
        await interaction.message.edit(content="▶️ Şarkı durduruldu.", view=None)
        self.stop()  # View'u kapat

    @discord.ui.button(label="Devam Et", style=discord.ButtonStyle.green)
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.player.voice.is_playing():
            await interaction.response.send_message("Zaten oynatılıyor.", ephemeral=True)
            return
        self.player.voice.resume()
        await interaction.response.send_message("▶️ Oynatma devam ediyor.", ephemeral=True)

    @discord.ui.button(label="Atla", style=discord.ButtonStyle.gray)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.voice is None or interaction.user.voice.channel != self.player.voice.channel:
            await interaction.response.send_message("Sesli kanalda değilsin!", ephemeral=True)
            return
        self.player.voice.stop()
        await interaction.response.send_message("⏭ Şarkı atlandı.", ephemeral=True)

    @discord.ui.button(label="Tekrarla", style=discord.ButtonStyle.blurple)
    async def repeat(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.voice is None or interaction.user.voice.channel != self.player.voice.channel:
            await interaction.response.send_message("Sesli kanalda değilsin!", ephemeral=True)
            return
        # Tekrar çalmak için aynı kaynağı yeniden oynat
        self.player.voice.stop()
        self.player.play_current()
        await interaction.response.send_message("🔁 Şarkı tekrar çalınıyor.", ephemeral=True)

class MusicPlayer:
    def __init__(self, bot, guild_id):
        self.bot = bot
        self.guild_id = guild_id
        self.queue = []
        self.voice = None
        self.current = None

    async def join(self, channel):
        if self.voice and self.voice.is_connected():
            if self.voice.channel.id == channel.id:
                return
            await self.voice.move_to(channel)
        else:
            self.voice = await channel.connect()

    async def leave(self):
        if self.voice and self.voice.is_connected():
            await self.voice.disconnect()
            self.voice = None

    def play_current(self):
        if not self.current:
            return
        source = discord.FFmpegPCMAudio(self.current['url'], **ffmpeg_options)
        self.voice.play(source, after=lambda e: self.bot.loop.create_task(self.play_next()))

    async def play_next(self):
        if self.queue:
            self.current = self.queue.pop(0)
            source = discord.FFmpegPCMAudio(self.current['url'], **ffmpeg_options)
            self.voice.play(source, after=lambda e: self.bot.loop.create_task(self.play_next()))
            channel = self.voice.channel
            # Kanal mesajına embed atmak istiyoruz, örnek için simple print
            # Burada şarkı bilgisi ve butonları atabiliriz.
        else:
            self.current = None
            await self.leave()

async def search_youtube(query):
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch5:{query}", download=False))
    return data['entries'] if 'entries' in data else [data]

@bot.tree.command(name="katıl", description="Botu ses kanalına çağırır")
async def join(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("Önce bir ses kanalına girmen gerekiyor.", ephemeral=True)
        return
    guild_id = interaction.guild.id
    if guild_id not in queues:
        queues[guild_id] = MusicPlayer(bot, guild_id)
    player = queues[guild_id]
    await player.join(interaction.user.voice.channel)
    await interaction.response.send_message(f"✅ {interaction.user.voice.channel.name} kanalına katıldım.")

@bot.tree.command(name="ayrıl", description="Botu ses kanalından çıkarır")
async def leave(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if guild_id not in queues or not queues[guild_id].voice:
        await interaction.response.send_message("Ben herhangi bir ses kanalında değilim.", ephemeral=True)
        return
    player = queues[guild_id]
    await player.leave()
    await interaction.response.send_message("✅ Ses kanalından ayrıldım.")

@bot.tree.command(name="oynat", description="Şarkı oynat")
@app_commands.describe(sarki="Aranacak şarkı adı")
@app_commands.autocomplete(sarki=lambda interaction, current: [app_commands.Choice(name=x, value=x) for x in ["Believer", "Shape of You", "Faded", "Despacito"] if current.lower() in x.lower()])
async def play(interaction: discord.Interaction, sarki: str):
    guild_id = interaction.guild.id
    if guild_id not in queues:
        queues[guild_id] = MusicPlayer(bot, guild_id)
    player = queues[guild_id]
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("Önce bir ses kanalına girmen gerekiyor.", ephemeral=True)
        return
    await player.join(interaction.user.voice.channel)

    # Youtube araması yap
    results = await search_youtube(sarki)
    if not results:
        await interaction.response.send_message("🎵 Şarkı bulunamadı.", ephemeral=True)
        return

    song = results[0]
    url = song['url']
    title = song['title']
    uploader = song.get('uploader', 'Bilinmeyen')
    duration = song.get('duration', 0)
    duration_min = f"{duration//60}:{duration%60:02d}"

    # Kuyruğa ekle
    player.queue.append({
        'title': title,
        'url': url,
        'uploader': uploader,
        'duration': duration_min
    })

    if not player.voice.is_playing() and not player.voice.is_paused():
        player.current = player.queue.pop(0)
        source = discord.FFmpegPCMAudio(player.current['url'], **ffmpeg_options)
        player.voice.play(source, after=lambda e: bot.loop.create_task(player.play_next()))

    embed = discord.Embed(title="🎶 Şarkı Çalınıyor", description=f"**{title}**\n\nSanatçı: {uploader}\nSüre: {duration_min}")
    view = MusicControls(player)
    await interaction.response.send_message(embed=embed, view=view)

bot.run("TOKEN")

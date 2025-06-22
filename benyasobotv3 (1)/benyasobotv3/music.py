import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Autocomplete fonksiyonu sınıf dışı, async coroutine olmalı
async def autocomplete_youtube(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name="Test Seçeneği 1", value="https://youtube.com"),
        app_commands.Choice(name="Test Seçeneği 2", value="https://youtube.com"),
    ]

    def blocking_search():
        try:
            info = ytdl.extract_info(current, download=False)
            return info.get('entries', [])
        except Exception as e:
            print(f"YTDL autocomplete error: {e}")
            return []
            
    results = await loop.run_in_executor(None, blocking_search)

    choices = []
    for entry in results[:5]:
        title = entry.get('title')
        url = entry.get('webpage_url')
        if title and url:
            display_title = title if len(title) <= 25 else title[:22] + "..."
            choices.append(app_commands.Choice(name=display_title, value=url))

    if not choices:
        choices.append(app_commands.Choice(name="Seçenek bulunamadı", value="https://youtu.be/dQw4w9WgXcQ"))

    return choices

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queues = {}
        self.executor = ThreadPoolExecutor(max_workers=3)

        ytdl_format_options = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'default_search': 'ytsearch',
            'source_address': '0.0.0.0',
            'http_headers': {'User-Agent': 'Mozilla/5.0'},
        }
        self.ffmpeg_options = {
            'options': '-vn',
        }
        self.ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

    async def play_next(self, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        voice_client = guild.voice_client
        if guild_id not in self.queues or len(self.queues[guild_id]) == 0:
            if voice_client and voice_client.is_connected():
                await voice_client.disconnect()
            return

        title, url = self.queues[guild_id].pop(0)
        source = discord.FFmpegPCMAudio(url, **self.ffmpeg_options)

        def after_play(error):
            coro = self.play_next(guild_id)
            fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error in after_play: {e}")

        voice_client.play(source, after=after_play)
        channel = voice_client.channel
        asyncio.run_coroutine_threadsafe(
            channel.send(f"🎶 Şimdi çalıyor: **{title}**", view=ControlButtons(self, guild_id)),
            self.bot.loop
        )

    @app_commands.command(name="katıl", description="Botu ses kanalınıza çağırır")
    async def katil(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("Öncelikle bir ses kanalına katılmalısın!", ephemeral=True)
            return

        user_channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        if voice_client:
            if voice_client.channel.id == user_channel.id:
                await interaction.response.send_message("Zaten bu ses kanalındayım.", ephemeral=True)
                return
            else:
                await voice_client.move_to(user_channel)
                await interaction.response.send_message(f"{user_channel.name} kanalına geçtim.")
        else:
            await user_channel.connect()
            await interaction.response.send_message(f"{user_channel.name} kanalına katıldım.")

    @app_commands.command(name="ayrıl", description="Botu ses kanalından çıkarır")
    async def ayril(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            await interaction.response.send_message("Ses kanalından ayrıldım.")
        else:
            await interaction.response.send_message("Ben hiçbir ses kanalında değilim.", ephemeral=True)

    @app_commands.command(name="oynat", description="YouTube'dan şarkı oynatır")
    @app_commands.describe(query="Oynatılacak şarkı adı veya arama terimi")
    @app_commands.autocomplete(query=autocomplete_youtube)  # Buraya fonksiyonun referansı geliyor
    async def oyna(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("Öncelikle bir ses kanalına katılmalısın!", ephemeral=True)
            return

        user_channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        if not voice_client or not voice_client.is_connected():
            await user_channel.connect()
            voice_client = interaction.guild.voice_client
        elif voice_client.channel.id != user_channel.id:
            await voice_client.move_to(user_channel)

        loop = asyncio.get_event_loop()
        try:
            info = await loop.run_in_executor(self.executor, lambda: self.ytdl.extract_info(query, download=False))
            title = info.get('title', 'Bilinmeyen Parça')
            url = info.get('url') or info.get('webpage_url') or query
        except Exception:
            title = "Bilinmeyen Parça"
            url = query

        guild_id = interaction.guild.id
        if guild_id not in self.queues:
            self.queues[guild_id] = []

        self.queues[guild_id].append((title, url))

        if not voice_client.is_playing():
            await interaction.response.send_message(f"**{title}** kuyruğa eklendi ve oynatılıyor.")
            await self.play_next(guild_id)
        else:
            await interaction.response.send_message(f"**{title}** kuyruğa eklendi.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        guild = member.guild
        voice_client = guild.voice_client
        if not voice_client or not voice_client.is_connected():
            return

        vc = voice_client.channel
        if vc and len(vc.members) == 1:
            await voice_client.disconnect()

class ControlButtons(discord.ui.View):
    def __init__(self, music_cog: Music, guild_id: int):
        super().__init__(timeout=180)
        self.music_cog = music_cog
        self.guild_id = guild_id

    @discord.ui.button(label="⏸️ Duraklat", style=discord.ButtonStyle.primary)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_playing():
            await interaction.response.send_message("Şu anda oynatılan bir şarkı yok.", ephemeral=True)
            return
        voice_client.pause()
        await interaction.response.send_message("⏸️ Oynatma duraklatıldı.", ephemeral=True)

    @discord.ui.button(label="▶️ Devam Ettir", style=discord.ButtonStyle.success)
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_paused():
            await interaction.response.send_message("Şu anda duraklatılmış bir şarkı yok.", ephemeral=True)
            return
        voice_client.resume()
        await interaction.response.send_message("▶️ Oynatma devam ettirildi.", ephemeral=True)

    @discord.ui.button(label="⏭️ Atla", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_playing():
            await interaction.response.send_message("Atlanacak şarkı yok.", ephemeral=True)
            return
        voice_client.stop()
        await interaction.response.send_message("⏭️ Şarkı atlandı.", ephemeral=True)

    @discord.ui.button(label="⏹️ Durdur", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        if not voice_client or (not voice_client.is_playing() and not voice_client.is_paused()):
            await interaction.response.send_message("Şu anda çalan bir şarkı yok.", ephemeral=True)
            return
        self.music_cog.queues[self.guild_id] = []
        voice_client.stop()
        await interaction.response.send_message("⏹️ Oynatma durduruldu ve kuyruk temizlendi.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
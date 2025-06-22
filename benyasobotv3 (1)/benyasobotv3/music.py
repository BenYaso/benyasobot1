import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio

# Basit şarkı bilgisi classı
class Song:
    def __init__(self, url, title, duration, artist):
        self.url = url
        self.title = title
        self.duration = duration
        self.artist = artist

    def formatted_duration(self):
        mins, secs = divmod(self.duration, 60)
        return f"{mins}:{secs:02d}"

class MusicPlayer:
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.current = None
        self.voice_client = None
        self.playing_message = None
        self.repeat = False

    async def join(self, ctx):
        if ctx.voice_client:
            self.voice_client = ctx.voice_client
            return
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.response.send_message("Lütfen bir ses kanalına katıl!", ephemeral=True)
            return
        channel = ctx.author.voice.channel
        self.voice_client = await channel.connect()

    async def leave(self):
        if self.voice_client:
            await self.voice_client.disconnect()
            self.voice_client = None
            self.queue.clear()
            self.current = None
            self.playing_message = None

    async def play_next(self):
        if not self.queue:
            self.current = None
            if self.playing_message:
                try:
                    await self.playing_message.edit(content="🎵 Sırada şarkı yok.", view=None)
                except:
                    pass
            if self.voice_client:
                await self.voice_client.disconnect()
                self.voice_client = None
            return

        self.current = self.queue.pop(0)
        source = discord.FFmpegPCMAudio(self.current.url)

        def after_playing(error):
            fut = asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error after playing: {e}")

        if self.voice_client.is_playing():
            self.voice_client.stop()

        self.voice_client.play(source, after=after_playing)

        content = (
            f"🎶 **Şarkı çalınıyor:** {self.current.title}\n"
            f"Sanatçı: {self.current.artist}  |  Süre: {self.current.formatted_duration()}"
        )

        view = ControlView(self)
        if self.playing_message:
            try:
                await self.playing_message.edit(content=content, view=view)
            except:
                self.playing_message = None
        if not self.playing_message:
            channel = self.voice_client.channel
            try:
                self.playing_message = await channel.send(content, view=view)
            except:
                pass

    async def add_song(self, song):
        self.queue.append(song)
        if not self.voice_client or not self.voice_client.is_playing():
            await self.play_next()

    def stop(self):
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()

    def pause(self):
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()

    def resume(self):
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()

    def skip(self):
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()

    def toggle_repeat(self):
        self.repeat = not self.repeat
        return self.repeat

class ControlView(discord.ui.View):
    def __init__(self, player: MusicPlayer):
        super().__init__(timeout=None)
        self.player = player

    @discord.ui.button(label="Durdur", style=discord.ButtonStyle.red)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player.stop()
        await interaction.response.send_message("⏹️ Müzik durduruldu.", ephemeral=True)

    @discord.ui.button(label="Durdur/Devam", style=discord.ButtonStyle.green)
    async def pause_resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.player.voice_client
        if not vc:
            await interaction.response.send_message("Bot ses kanalında değil.", ephemeral=True)
            return
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Müzik duraklatıldı.", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Müzik devam ettirildi.", ephemeral=True)
        else:
            await interaction.response.send_message("Şu anda çalan müzik yok.", ephemeral=True)

    @discord.ui.button(label="Atla", style=discord.ButtonStyle.blurple)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player.skip()
        await interaction.response.send_message("⏭️ Şarkı atlandı.", ephemeral=True)

    @discord.ui.button(label="Tekrarla", style=discord.ButtonStyle.gray)
    async def repeat_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        status = self.player.toggle_repeat()
        await interaction.response.send_message(f"🔁 Tekrar modı {'aktif' if status else 'kapalı'}.", ephemeral=True)

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.player = MusicPlayer(bot)
        self.ytdlp_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "default_search": "ytsearch",
        }

    @app_commands.command(name="katıl", description="Ses kanalına katılır")
    async def join(self, interaction: discord.Interaction):
        await self.player.join(interaction)
        await interaction.response.send_message("✅ Ses kanalına katıldı!", ephemeral=True)

    @app_commands.command(name="ayrıl", description="Ses kanalından ayrılır")
    async def leave(self, interaction: discord.Interaction):
        await self.player.leave()
        await interaction.response.send_message("✅ Ses kanalından ayrıldı!", ephemeral=True)

    @app_commands.command(name="oynat", description="Şarkı arat ve çal")
    @app_commands.describe(sorgu="Şarkı adı veya link")
    @app_commands.autocomplete(sorgu="autocomplete_songs")
    async def play(self, interaction: discord.Interaction, sorgu: str):
        await interaction.response.defer()
        # YouTube araması
        with yt_dlp.YoutubeDL(self.ytdlp_opts) as ytdl:
            try:
                info = ytdl.extract_info(sorgu, download=False)
                if "entries" in info:
                    info = info["entries"][0]
            except Exception as e:
                await interaction.followup.send(f"❌ Şarkı bulunamadı: {e}")
                return

        url = info["url"]
        title = info.get("title", "Bilinmeyen")
        duration = info.get("duration", 0)
        artist = info.get("artist") or info.get("uploader") or "Bilinmeyen"

        song = Song(url, title, duration, artist)

        await self.player.add_song(song)

        await interaction.followup.send(f"🎶 Şarkı sıraya eklendi: **{title}**")

@app_commands.autocomplete(sorgu=autocomplete_songs)
async def autocomplete_songs(self, interaction: discord.Interaction, current: str):
    options = [
        "Never Gonna Give You Up",
        "Blinding Lights",
        "Shape of You",
        "Believer",
        "Faded",
        "Counting Stars",
        "Someone Like You",
    ]
    return [
        app_commands.Choice(name=opt, value=opt)
        for opt in options if current.lower() in opt.lower()
    ][:5]

async def setup(bot):
    await bot.add_cog(MusicCog(bot))

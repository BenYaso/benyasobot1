import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio

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

    async def join(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("Bu komut sadece sunucularda kullanılabilir.", ephemeral=True)
            return False

        if interaction.guild.voice_client:
            self.voice_client = interaction.guild.voice_client
            return True

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("Lütfen bir ses kanalına katıl!", ephemeral=True)
            return False

        channel = interaction.user.voice.channel
        self.voice_client = await channel.connect()
        return True

    async def leave(self):
        if self.voice_client:
            await self.voice_client.disconnect()
            self.voice_client = None
            self.queue.clear()
            self.current = None
            self.playing_message = None

    async def play_next(self):
        if not self.queue and not self.repeat:
            self.current = None
            if self.playing_message:
                try:
                    await self.playing_message.edit(content="🎵 Sırada şarkı yok.", view=None)
                except Exception as e:
                    print(f"play_next edit mesaj hatası: {e}")
                self.playing_message = None

            if self.voice_client:
                await self.voice_client.disconnect()
                self.voice_client = None
            return

        if self.repeat and self.current:
            song = self.current
        else:
            song = self.queue.pop(0)
            self.current = song

        source = discord.FFmpegPCMAudio(song.url)

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
            f"🎶 **Şarkı çalınıyor:** {song.title}\n"
            f"Sanatçı: {song.artist}  |  Süre: {song.formatted_duration()}\n\n"
            f"**Şarkı çalınıyor...**"
        )

        view = ControlView(self)
        if self.playing_message:
            try:
                await self.playing_message.edit(content=content, view=view)
            except Exception as e:
                print(f"play_next mesaj güncelleme hatası: {e}")
                self.playing_message = None

        if not self.playing_message:
            try:
                self.playing_message = await self.voice_client.channel.send(content, view=view)
            except Exception as e:
                print(f"play_next mesaj gönderme hatası: {e}")

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

    @app_commands.command(name="katıl", description="Ses kanalına katılır")
    async def join(self, interaction: discord.Interaction):
        # İlk olarak defer yapıyoruz
        await interaction.response.defer()
        success = await self.player.join(interaction)
        if success:
            await interaction.followup.send("✅ Ses kanalına katıldı!", ephemeral=True)

    @app_commands.command(name="ayrıl", description="Ses kanalından ayrılır")
    async def leave(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.player.leave()
        await interaction.followup.send("✅ Ses kanalından ayrıldı!", ephemeral=True)

    @app_commands.command(name="oynat", description="Şarkı arat ve çal")
    @app_commands.describe(sorgu="Şarkı adı veya link")
    @app_commands.autocomplete(sorgu=autocomplete_songs)
    async def play(self, interaction: discord.Interaction, sorgu: str):
        await interaction.response.defer()

        with yt_dlp.YoutubeDL(self.ytdlp_opts) as ytdl:
            try:
                info = ytdl.extract_info(sorgu, download=False)
                if "entries" in info:
                    info = info["entries"][0]
            except Exception as e:
                await interaction.followup.send(f"❌ Şarkı bulunamadı: {e}", ephemeral=True)
                return

        url = info.get("url")
        # Bazı durumlarda "url" yerine "formats" listesinde stream url olabilir
        if not url and "formats" in info:
            for f in info["formats"]:
                if f.get("acodec") != "none" and f.get("vcodec") == "none":
                    url = f.get("url")
                    break

        if not url:
            await interaction.followup.send("❌ Şarkı oynatmak için geçerli bir URL bulunamadı.", ephemeral=True)
            return

        title = info.get("title", "Bilinmeyen")
        duration = info.get("duration", 0)
        artist = info.get("artist") or info.get("uploader") or "Bilinmeyen"

        song = Song(url, title, duration, artist)

        await self.player.add_song(song)

        await interaction.followup.send(f"🎶 Şarkı sıraya eklendi: **{title}**")

async def setup(bot):
    await bot.add_cog(MusicCog(bot))

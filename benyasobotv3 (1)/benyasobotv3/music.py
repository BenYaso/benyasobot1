import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}

        self.YTDL_OPTIONS = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'extract_flat': 'in_playlist',
            'default_search': 'ytsearch5:',
            'source_address': '0.0.0.0'  # ipv4
        }

        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        self.ydl = yt_dlp.YoutubeDL(self.YTDL_OPTIONS)
        self.now_playing = {}

    async def search_song(self, query):
        info = self.ydl.extract_info(query, download=False)
        if 'entries' in info:
            return info['entries'][0]
        return info

    @app_commands.command(name="katıl", description="Ses kanalına katılır.")
    async def join(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("🎧 Ses kanalında değilsin.", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client
        if vc and vc.is_connected():
            await vc.move_to(channel)
        else:
            await channel.connect()

        await interaction.response.send_message(f"🎶 {channel.name} kanalına bağlandım.")

    @app_commands.command(name="ayrıl", description="Ses kanalından ayrılır.")
    async def leave(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_connected():
            await vc.disconnect()
            await interaction.response.send_message("📴 Ses kanalından ayrıldım.")
        else:
            await interaction.response.send_message("❌ Bot herhangi bir ses kanalına bağlı değil.", ephemeral=True)

    @app_commands.command(name="oynat", description="Şarkı arar ve oynatır.")
    @app_commands.describe(sarki="Şarkı adı veya URL")
    async def play(self, interaction: discord.Interaction, sarki: str):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("🎧 Ses kanalında değilsin.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            info = await asyncio.to_thread(self.search_song, sarki)
        except Exception as e:
            await interaction.followup.send(f"❌ Şarkı bulunamadı: {e}")
            return

        url = info['url'] if 'url' in info else info['webpage_url']
        title = info.get('title', 'Bilinmeyen Şarkı')
        duration = int(info.get('duration', 0))
        uploader = info.get('uploader', 'Bilinmeyen')

        minutes, seconds = divmod(duration, 60)
        duration_str = f"{minutes}:{seconds:02d}"

        channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            vc = await channel.connect()
        elif vc.channel != channel:
            await vc.move_to(channel)

        # Çalma işlemi
        def after_playing(error):
            coro = interaction.channel.send(f"▶️ **{title}** bitti.")
            fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
            try:
                fut.result()
            except:
                pass

        source = discord.FFmpegPCMAudio(url, **self.FFMPEG_OPTIONS)
        if vc.is_playing():
            vc.stop()
        vc.play(source, after=after_playing)

        # Mesaj gönderelim
        embed = discord.Embed(title="🎵 Şarkı Çalınıyor", description=f"**{title}**", color=0x1DB954)
        embed.add_field(name="Sanatçı", value=uploader, inline=True)
        embed.add_field(name="Süre", value=duration_str, inline=True)
        embed.set_footer(text="Şarkı çalınıyor...")

        # Durdur / Devam / Atla / Tekrarla Butonları
        class MusicButtons(discord.ui.View):
            def __init__(self, vc):
                super().__init__(timeout=None)
                self.vc = vc
                self.loop = False

            @discord.ui.button(label="Durdur", style=discord.ButtonStyle.red)
            async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if not self.vc.is_playing():
                    await interaction.response.send_message("Zaten oynatma yok.", ephemeral=True)
                    return
                self.vc.stop()
                await interaction.response.send_message("⏹️ Şarkı durduruldu.", ephemeral=True)

            @discord.ui.button(label="Devam", style=discord.ButtonStyle.green)
            async def resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.vc.is_playing():
                    await interaction.response.send_message("Zaten çalıyor.", ephemeral=True)
                    return
                self.vc.resume()
                await interaction.response.send_message("▶️ Devam edildi.", ephemeral=True)

            @discord.ui.button(label="Atla", style=discord.ButtonStyle.blurple)
            async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.vc.is_playing():
                    self.vc.stop()
                    await interaction.response.send_message("⏭️ Şarkı atlandı.", ephemeral=True)
                else:
                    await interaction.response.send_message("Şu anda şarkı çalmıyor.", ephemeral=True)

            @discord.ui.button(label="Tekrarla", style=discord.ButtonStyle.gray)
            async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.loop = not self.loop
                durum = "aktif" if self.loop else "pasif"
                await interaction.response.send_message(f"🔁 Tekrar mod {durum}.", ephemeral=True)

        view = MusicButtons(vc)
        self.now_playing[interaction.guild.id] = {"info": info, "loop": False}
        await interaction.followup.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Music(bot))

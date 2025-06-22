from discord.ext import commands, tasks
from discord import app_commands
import discord
import feedparser
import json
import os

# Ayarlar
RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UCTYeNjk3VZnXNfcC8ssvevQ"
VIDEO_KANAL_ID = 1385320019545686046  # Video duyuru kanal ID
LIVE_KANAL_ID = 1385351597026050068   # Canlı yayın kanal ID
EMOJI = "<a:duyuru:1385455672841211984>"  # Sunucuya özel emoji

class YouTubeBildirim(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_video_file = "last_video.json"
        self.last_video_id = self.load_last_video_id()
        self.check_feed.start()

    def load_last_video_id(self):
        if os.path.exists(self.last_video_file):
            with open(self.last_video_file, "r") as f:
                return json.load(f).get("video_id", None)
        return None

    def save_last_video_id(self, video_id):
        with open(self.last_video_file, "w") as f:
            json.dump({"video_id": video_id}, f)

    @tasks.loop(minutes=5)
    async def check_feed(self):
        try:
            feed = feedparser.parse(RSS_URL)
            latest_entry = feed.entries[0]
            video_id = latest_entry.yt_videoid
            video_url = latest_entry.link
            title = latest_entry.title

            if video_id != self.last_video_id:
                self.last_video_id = video_id
                self.save_last_video_id(video_id)

                kanal = self.bot.get_channel(VIDEO_KANAL_ID)
                if kanal:
                    await kanal.send(f"{EMOJI} **Yeni video yayında!**\n📹 {title}\n{video_url}")
        except Exception as e:
            print(f"[RSS] Hata oluştu: {e}")

    @check_feed.before_loop
    async def before_check_feed(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="ytdeneme", description="YouTube video bildirimi test mesajı gönderir.")
    async def ytdeneme(self, interaction: discord.Interaction):
        kanal = self.bot.get_channel(VIDEO_KANAL_ID)
        if kanal:
            await kanal.send(f"{EMOJI} **Test bildirimi:** Bu bir video test mesajıdır.")
            await interaction.response.send_message("✅ Video test bildirimi gönderildi.", ephemeral=True)
        else:
            await interaction.response.send_message("📛 Video kanalı bulunamadı.", ephemeral=True)

    @app_commands.command(name="canlıdeneme", description="Canlı yayın bildirimi test mesajı gönderir.")
    async def canlıdeneme(self, interaction: discord.Interaction):
        kanal = self.bot.get_channel(LIVE_KANAL_ID)
        if kanal:
            await kanal.send(f"{EMOJI} **Canlı yayın başladı!**\n🔴 Şu an yayındayız! Katıl: https://youtube.com/@BenYasoMinecraft/live")
            await interaction.response.send_message("✅ Canlı yayın test bildirimi gönderildi.", ephemeral=True)
        else:
            await interaction.response.send_message("📛 Canlı yayın kanalı bulunamadı.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(YouTubeBildirim(bot))
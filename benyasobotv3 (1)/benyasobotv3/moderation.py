import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from typing import Optional
import random

MUTED_ROLE_NAME = "Muted"
MUTE_LOG_KANAL_ID = 1385381927971852411  # Susturma kalkınca bildirim gidecek kanal ID'si

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Botun gecikme süresini gösterir.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! Gecikme: {round(self.bot.latency * 1000)} ms")

    @app_commands.command(name="sil", description="Mesajları temizler. (Yetkili)")
    @app_commands.describe(miktar="Silinecek mesaj sayısı")
    async def sil(self, interaction: discord.Interaction, miktar: int):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Bu komutu kullanmak için mesajları yönetme yetkin olmalı.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)  # Hemen cevap verildiğini bildir

        deleted = await interaction.channel.purge(limit=miktar)

        await interaction.followup.send(f"🧹 {len(deleted)} mesaj silindi.", ephemeral=True)

    @app_commands.command(name="oylama", description="Oylama başlatır. (Yetkili)")
    @app_commands.describe(soru="Oylama sorusu ve şıkları, aralarında virgül ile")
    async def oylama(self, interaction: discord.Interaction, soru: str):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Bu komutu kullanmak için mesajları yönetme yetkin olmalı.", ephemeral=True)
            return

        parçalar = [p.strip() for p in soru.split(",")]
        if len(parçalar) < 2:
            await interaction.response.send_message("⚠️ Lütfen oylama sorusu ve en az iki şık girin, örn: Soru,Şık1,Şık2", ephemeral=True)
            return

        soru_metni = parçalar[0]
        şıklar = parçalar[1:]
        if len(şıklar) > 10:
            await interaction.response.send_message("⚠️ Maksimum 10 şık olabilir.", ephemeral=True)
            return

        emoji_listesi = ['1️⃣','2️⃣','3️⃣','4️⃣','5️⃣','6️⃣','7️⃣','8️⃣','9️⃣','🔟']

        oy_mesaj = f"📊 **OYLAMA:** {soru_metni}\n"
        for i, şık in enumerate(şıklar):
            oy_mesaj += f"{emoji_listesi[i]} {şık}\n"

        mesaj = await interaction.channel.send(oy_mesaj)
        for i in range(len(şıklar)):
            await mesaj.add_reaction(emoji_listesi[i])

        await interaction.response.send_message("✅ Oylama başlatıldı!", ephemeral=True)

    @app_commands.command(name="yasakla", description="Kullanıcıyı sunucudan yasaklar. (Yetkili)")
    @app_commands.describe(kullanıcı="Yasaklanacak kullanıcı", sebep="Sebep")
    async def yasakla(self, interaction: discord.Interaction, kullanıcı: discord.Member, sebep: Optional[str] = "Sebep belirtilmedi."):
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message("❌ Yasaklama yetkin yok.", ephemeral=True)
            return

        try:
            await kullanıcı.ban(reason=sebep)
            await interaction.response.send_message(f"✅ {kullanıcı.mention} yasaklandı. Sebep: {sebep}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Yasaklama başarısız: {e}", ephemeral=True)

    @app_commands.command(name="at", description="Kullanıcıyı sunucudan atar. (Yetkili)")
    @app_commands.describe(kullanıcı="Atılacak kullanıcı", sebep="Sebep")
    async def at(self, interaction: discord.Interaction, kullanıcı: discord.Member, sebep: Optional[str] = "Sebep belirtilmedi."):
        if not interaction.user.guild_permissions.kick_members:
            await interaction.response.send_message("❌ Atma yetkin yok.", ephemeral=True)
            return

        try:
            await kullanıcı.kick(reason=sebep)
            await interaction.response.send_message(f"✅ {kullanıcı.mention} sunucudan atıldı. Sebep: {sebep}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Atma başarısız: {e}", ephemeral=True)

    @app_commands.command(name="sustur", description="Kullanıcıyı belirli bir süre susturur.")
    @app_commands.describe(süre="Süre: 10s, 5m, 1h", sebep="Sebep belirtin")
    async def sustur(self, interaction: discord.Interaction, kullanıcı: discord.Member, süre: str, sebep: str = "Sebep belirtilmedi."):
        mute_rol = discord.utils.get(interaction.guild.roles, name=MUTED_ROLE_NAME)
        if mute_rol is None:
            await interaction.response.send_message(f"❌ '{MUTED_ROLE_NAME}' adlı rol bulunamadı.", ephemeral=True)
            return

        süre_map = {"s": 1, "m": 60, "h": 3600}
        try:
            saniye = int(süre[:-1]) * süre_map[süre[-1]]
        except:
            await interaction.response.send_message("⚠️ Süreyi `10s`, `5m`, `1h` gibi yazmalısın.", ephemeral=True)
            return

        await kullanıcı.add_roles(mute_rol, reason=sebep)
        await interaction.response.send_message(f"🔇 {kullanıcı.mention} {süre} süreyle susturuldu. Sebep: {sebep}")

        self.bot.loop.create_task(self.susturmayı_takip_et(kullanıcı, mute_rol, saniye, interaction.guild))

    async def susturmayı_takip_et(self, kullanıcı, mute_rol, saniye, guild):
        await asyncio.sleep(saniye)
        try:
            await kullanıcı.remove_roles(mute_rol)
        except Exception as e:
            print(f"❌ Susturma kaldırılırken hata: {e}")
            return

        kanal = self.bot.get_channel(MUTE_LOG_KANAL_ID)
        if kanal:
            await kanal.send(f"🔔 {kullanıcı.mention} adlı kullanıcının susturulması sona erdi.")

    @app_commands.command(name="susturmakaldır", description="Kullanıcının susturmasını kaldırır.")
    async def susturmakaldır(self, interaction: discord.Interaction, kullanıcı: discord.Member):
        mute_rol = discord.utils.get(interaction.guild.roles, name=MUTED_ROLE_NAME)
        if mute_rol is None:
            await interaction.response.send_message(f"❌ '{MUTED_ROLE_NAME}' adlı rol bulunamadı.", ephemeral=True)
            return

        await kullanıcı.remove_roles(mute_rol)
        await interaction.response.send_message(f"🔊 {kullanıcı.mention} adlı kullanıcının susturması kaldırıldı.")

    @app_commands.command(name="sunucubilgi", description="Sunucu bilgilerini gösterir.")
    async def sunucubilgi(self, interaction: discord.Interaction):
        guild = interaction.guild
        mesaj = (
            f"**Sunucu Adı:** {guild.name}\n"
            f"**Sunucu ID:** {guild.id}\n"
            f"**Üye Sayısı:** {guild.member_count}\n"
            f"**Oluşturulma Tarihi:** {guild.created_at.strftime('%d-%m-%Y')}\n"
            f"**Bölge:** {guild.region if hasattr(guild, 'region') else 'Bölge bilgisi yok'}"
        )
        await interaction.response.send_message(mesaj)

    @app_commands.command(name="uyarı", description="Kullanıcıyı uyarır. (Yetkili)")
    @app_commands.describe(kullanıcı="Uyarılacak kişi", sebep="Sebep")
    async def uyarı(self, interaction: discord.Interaction, kullanıcı: discord.Member, sebep: Optional[str] = "Sebep belirtilmedi."):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Uyarı yetkin yok.", ephemeral=True)
            return

        # Buraya kendi uyarı sistemi kodunu ekleyebilirsin.
        await interaction.response.send_message(f"⚠️ {kullanıcı.mention} uyarıldı. Sebep: {sebep}")

    @app_commands.command(name="uyarıliste", description="Uyarı listesini gösterir. (Yetkili)")
    async def uyarıliste(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Yetkin yok.", ephemeral=True)
            return

        # Buraya uyarı listesini çekme kodunu ekleyebilirsin.
        await interaction.response.send_message("📋 Uyarı listesi şuan boş ya da sistem kurulmamış.")

    @app_commands.command(name="uyarısil", description="Kullanıcının tüm uyarılarını siler. (Yetkili)")
    @app_commands.describe(kullanıcı="Uyarıları silinecek kişi")
    async def uyarısil(self, interaction: discord.Interaction, kullanıcı: discord.Member):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Yetkin yok.", ephemeral=True)
            return

        # Buraya uyarı silme kodunu ekleyebilirsin.
        await interaction.response.send_message(f"✅ {kullanıcı.mention} adlı kullanıcının uyarıları silindi.")

    @app_commands.command(name="tkm", description="Taş, Kağıt, Makas oynar. (DM'den yazınız!)")
    async def tkm(self, interaction: discord.Interaction):
        if interaction.guild is not None:
            await interaction.response.send_message("❌ Bu komutu sadece DM'den kullanabilirsin.", ephemeral=True)
            return

        seçenekler = ["Taş", "Kağıt", "Makas"]
        bot_seçim = random.choice(seçenekler)
        await interaction.response.send_message(f"Ben **{bot_seçim}** seçtim! Sıra sende...")

    @app_commands.command(name="tahminet", description="Tahmin etme oyunu oynar. (DM'den yazınız!)")
    async def tahminet(self, interaction: discord.Interaction):
        if interaction.guild is not None:
            await interaction.response.send_message("❌ Bu komutu sadece DM'den kullanabilirsin.", ephemeral=True)
            return

        await interaction.response.send_message("Tahmin etme oyunu başlıyor! (Bu komut henüz tamamlanmadı.)")

    @app_commands.command(name="yardım", description="Tüm komutları gösterir.")
    async def yardım(self, interaction: discord.Interaction):
        komutlar = """
**Moderasyon Komutları:**
/ping - Botun gecikme süresini gösterir.
/sil <miktar> - Mesajları temizler. (Yetkili)
/oylama <soru,şık1,şık2,...> - Oylama başlatır. (Yetkili)
/yasakla @kullanıcı [sebep] - Sunucudan yasaklar. (Yetkili)
/at @kullanıcı [sebep] - Sunucudan atar. (Yetkili)
/sustur @kullanıcı <süre> [sebep] - Susturur. (Muted rolü gerekli)
/susturmakaldır @kullanıcı - Susturmayı kaldırır.
/sunucubilgi - Sunucu bilgilerini gösterir.
/uyarı @kullanıcı [sebep] - Kullanıcıyı uyarır. (Yetkili)
/uyarıliste - Uyarı listesini gösterir. (Yetkili)
/uyarısil @kullanıcı - Kullanıcının tüm uyarılarını siler. (Yetkili)
/tkm - Taş, Kağıt, Makas oynar. (DM'den)
/tahminet - Tahmin etme oyunu oynar. (DM'den)
/yardım - Tüm komutları gösterir.
"""
        await interaction.response.send_message(komutlar, ephemeral=True)

    @app_commands.command(name="duyuru", description="Sadece yetkililerin kullanabileceği bir duyuru komutu.")
    @app_commands.describe(mesaj="Gönderilecek duyuru metni")
    async def duyuru(self, interaction: discord.Interaction, mesaj: str):
        # Yalnızca 'Mesajları Yönet' yetkisi olanlar kullanabilir
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Bu komutu kullanmak için yeterli yetkin yok.", ephemeral=True)
            return

        try:
            await interaction.response.send_message("📢 Duyuru başarıyla gönderildi!", ephemeral=True)
            await interaction.channel.send(f" {mesaj}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Bir hata oluştu: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Moderation(bot))

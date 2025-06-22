import discord
from discord.ext import commands
import json
import asyncio
import time

MUTE_LOG_KANAL_ID = 1385381927971852411  # Susturma bildirimi atılacak kanal ID
MUTED_ROLE_NAME = "Muted"
UYARI_DOSYASI = "uyarı_data.json"
KÜFÜRLER = ["amk", "aq", "siktir", "orospu", "piç", "yarrak"]
SPAM_SINIRI = 5  # Kaç saniyede
SPAM_SAYISI = 4  # Kaç mesaj üstü spam sayılır
MUTE_SÜRESİ = 600  # 10 dakika = 600 saniye

class AutoMute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.son_mesajlar = {}  # Kullanıcı bazlı spam zamanlarını tutar
        self.uyarılar = self.uyarıları_yükle()

    def uyarıları_yükle(self):
        try:
            with open(UYARI_DOSYASI, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def uyarıları_kaydet(self):
        try:
            with open(UYARI_DOSYASI, "w") as f:
                json.dump(self.uyarılar, f, indent=4)
        except Exception as e:
            print(f"UYARI DOSYASI KAYDEDILEMEDI: {e}")

    def kullanıcıyı_uyar(self, guild_id, user_id):
        if guild_id not in self.uyarılar:
            self.uyarılar[guild_id] = {}
        if user_id not in self.uyarılar[guild_id]:
            self.uyarılar[guild_id][user_id] = 0
        self.uyarılar[guild_id][user_id] += 1
        self.uyarıları_kaydet()
        return self.uyarılar[guild_id][user_id]

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        guild_id = str(message.guild.id)
        user_id = str(message.author.id)
        içerik = message.content.lower()

        # --- Küfür filtresi ---
        if any(k in içerik for k in KÜFÜRLER):
            try:
                await message.delete()
            except:
                pass

            sayı = self.kullanıcıyı_uyar(guild_id, user_id)
            await message.channel.send(
                f"🚫 {message.author.mention}, küfür ettiği için uyarıldı. ({sayı}/5)", delete_after=5
            )

        # --- Spam filtresi ---
        zaman = time.time()
        if user_id not in self.son_mesajlar:
            self.son_mesajlar[user_id] = []
        self.son_mesajlar[user_id].append(zaman)
        # Son SPAM_SINIRI saniye içindeki mesajları tut
        self.son_mesajlar[user_id] = [t for t in self.son_mesajlar[user_id] if zaman - t <= SPAM_SINIRI]

        if len(self.son_mesajlar[user_id]) > SPAM_SAYISI:
            sayı = self.kullanıcıyı_uyar(guild_id, user_id)
            await message.channel.send(
                f"⚠️ {message.author.mention}, spam yaptığı için uyarıldı. ({sayı}/5)", delete_after=5
            )

        # --- 5. uyarıda mute işlemi ---
        uyarı_sayısı = self.uyarılar.get(guild_id, {}).get(user_id, 0)
        if uyarı_sayısı >= 5:
            muted_rol = discord.utils.get(message.guild.roles, name=MUTED_ROLE_NAME)
            if muted_rol and muted_rol not in message.author.roles:
                try:
                    await message.author.add_roles(muted_rol, reason="5 uyarıya ulaştı (otomatik mute)")
                    await message.channel.send(
                        f"🔇 {message.author.mention}, 5 uyarıya ulaştığı için {MUTE_SÜRESİ//60} dakika susturuldu."
                    )
                    # Uyarı sayısını sıfırla, mute spamı önlemek için
                    self.uyarılar[guild_id][user_id] = 0
                    self.uyarıları_kaydet()
                    self.bot.loop.create_task(self.muteyi_kaldır(message.author, muted_rol, MUTE_SÜRESİ, message.guild))
                except Exception as e:
                    print(f"Mute atılırken hata: {e}")

    async def muteyi_kaldır(self, kullanıcı, rol, süre, guild):
        await asyncio.sleep(süre)
        try:
            await kullanıcı.remove_roles(rol)
        except Exception as e:
            print(f"Rol kaldırılamadı: {e}")
            return

        kanal = self.bot.get_channel(MUTE_LOG_KANAL_ID)
        if kanal:
            await kanal.send(f"🔔 {kullanıcı.mention} adlı kullanıcının susturulması sona erdi (otomatik mute).")

async def setup(bot):
    await bot.add_cog(AutoMute(bot))

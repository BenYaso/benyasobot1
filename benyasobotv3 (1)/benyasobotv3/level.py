from discord.ext import commands
from discord import app_commands
import discord
import json
import os
import random
import datetime
import asyncio

GUILD_ID = 1385317817888411729  # kendi sunucu ID

class LevelSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.level_file = "level_data.json"
        self.weekly_file = "weekly_xp.json"  # Haftalık xp dosyası
        self.level_roles = {
            1: "Level 1",
            5: "Level 5",
            10: "Level 10",
            25: "Level 25",
            50: "Level 50",
            75: "Level 75",
            100: "Level 100",
            200: "Level 200",
            300: "Level 300",
            400: "Level 400",
            500: "Level 500"
        }
        self.load_data()
        self.load_weekly_data()
        # self.bot.loop.create_task(self.weekly_xp_report_task())  # Burayı kaldırdım

        async def cog_load(self):
            asyncio.create_task(self.weekly_xp_report_task())

    def load_data(self):
        try:
            if os.path.exists(self.level_file):
                with open(self.level_file, "r") as f:
                    self.levels = json.load(f)
            else:
                self.levels = {}
        except Exception as e:
            print(f"Veri yüklenirken hata: {e}")
            self.levels = {}

    def save_data(self):
        try:
            with open(self.level_file, "w") as f:
                json.dump(self.levels, f, indent=4)
        except Exception as e:
            print(f"Veri kaydedilirken hata: {e}")

    def load_weekly_data(self):
        try:
            if os.path.exists(self.weekly_file):
                with open(self.weekly_file, "r") as f:
                    self.weekly_levels = json.load(f)
            else:
                self.weekly_levels = {}
        except Exception as e:
            print(f"Haftalık veri yüklenirken hata: {e}")
            self.weekly_levels = {}

    def save_weekly_data(self):
        try:
            with open(self.weekly_file, "w") as f:
                json.dump(self.weekly_levels, f, indent=4)
        except Exception as e:
            print(f"Haftalık veri kaydedilirken hata: {e}")

    def get_level_xp(self, level):
        return 50 * level + 100

    def get_level_role(self, level):
        return self.level_roles.get(level)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None:
            return

        guild_id = str(message.guild.id)

        if "_disabled" in self.levels and self.levels["_disabled"].get(guild_id, False):
            return

        user_id = str(message.author.id)

        if guild_id not in self.levels:
            self.levels[guild_id] = {}
        if user_id not in self.levels[guild_id]:
            self.levels[guild_id][user_id] = {"xp": 0, "level": 1}

        # Haftalık xp için data kontrolü
        if guild_id not in self.weekly_levels:
            self.weekly_levels[guild_id] = {}
        if user_id not in self.weekly_levels[guild_id]:
            self.weekly_levels[guild_id][user_id] = 0

        data = self.levels[guild_id][user_id]
        xp_gain = random.randint(5, 15)
        data["xp"] += xp_gain

        # Haftalık xp ekle
        self.weekly_levels[guild_id][user_id] += xp_gain

        needed_xp = self.get_level_xp(data["level"])
        if data["xp"] >= needed_xp:
            data["xp"] -= needed_xp
            data["level"] += 1
            await message.channel.send(f"🎉 {message.author.mention}, **seviye {data['level']}** oldun!")

            role_name = self.get_level_role(data["level"])
            if role_name:
                role = discord.utils.get(message.guild.roles, name=role_name)
                if role:
                    # İşte eski level rollerini kaldırma kısmı burası:
                    for r in message.author.roles:
                        if r.name in self.level_roles.values() and r != role:
                            await message.author.remove_roles(r)
                    await message.author.add_roles(role)
                    await message.channel.send(f"✅ {role_name} rolünü kazandın!")

        self.save_data()
        self.save_weekly_data()

    @app_commands.command(name="xp", description="Kendi veya bir başkasının XP ve seviyesini gösterir.")
    async def xp(self, interaction: discord.Interaction, kullanıcı: discord.Member = None):
        kullanıcı = kullanıcı or interaction.user
        user_id = str(kullanıcı.id)
        guild_id = str(interaction.guild.id)

        if guild_id not in self.levels or user_id not in self.levels[guild_id]:
            await interaction.response.send_message(f"{kullanıcı.mention} için herhangi bir XP verisi bulunamadı.")
            return

        data = self.levels[guild_id][user_id]
        xp = data["xp"]
        level = data["level"]
        next_level_xp = self.get_level_xp(level)

        await interaction.response.send_message(
            f"📊 {kullanıcı.mention} • Seviye: {level} | XP: {xp}/{next_level_xp}"
        )

    @app_commands.command(name="rank", description="Sunucudaki en yüksek XP'ye sahip 10 kişiyi gösterir.")
    async def rank(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)

        if guild_id not in self.levels:
            await interaction.response.send_message("Henüz kimse XP kazanmamış.", ephemeral=True)
            return

        guild_data = self.levels[guild_id]
        sorted_members = sorted(
            guild_data.items(),
            key=lambda item: (item[1]["level"], item[1]["xp"]),
            reverse=True
        )

        message = "**🏆 En yüksek seviyedeki 10 kullanıcı:**\n"
        for i, (user_id, data) in enumerate(sorted_members[:10], start=1):
            member = interaction.guild.get_member(int(user_id))
            name = member.display_name if member else f"<@{user_id}>"
            message += f"**{i}.** {name} — Seviye {data['level']} ({data['xp']} XP)\n"

        await interaction.response.send_message(message)

    @app_commands.command(name="xpkapat", description="Sunucuda XP kazanımını devre dışı bırakır.")
    async def xpkapat(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)

        if "_disabled" not in self.levels:
            self.levels["_disabled"] = {}

        self.levels["_disabled"][guild_id] = True
        self.save_data()
        await interaction.response.send_message("❌ XP kazanımı bu sunucuda devre dışı bırakıldı.")

    @app_commands.command(name="xpaç", description="Sunucuda XP kazanımını yeniden aktif eder.")
    async def xpaç(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)

        if "_disabled" in self.levels and self.levels["_disabled"].get(guild_id):
            self.levels["_disabled"][guild_id] = False
            self.save_data()
            await interaction.response.send_message("✅ XP kazanımı bu sunucuda yeniden aktif edildi.")
        else:
            await interaction.response.send_message("ℹ️ XP kazanımı zaten açık.")

    async def weekly_xp_report_task(self):
        await self.bot.wait_until_ready()
        kanal_id = 1385646085988417687  # Haftalık XP mesajının atılacağı kanal ID'sini buraya yaz
        kanal = self.bot.get_channel(kanal_id)
        if kanal is None:
            print("Haftalık XP kanalı bulunamadı!")
            return

        while not self.bot.is_closed():
            now = datetime.datetime.utcnow()
            # Pazar günü UTC 20:00 kontrolü (Türkiye saati için ayarlayabilirsin)
            if now.weekday() == 6 and now.hour == 20 and now.minute == 0:
                guild_id = str(kanal.guild.id)
                if guild_id in self.weekly_levels:
                    weekly_data = self.weekly_levels[guild_id]
                    sorted_users = sorted(weekly_data.items(), key=lambda x: x[1], reverse=True)[:10]

                    mesaj = "**🏆 Haftalık XP sıralaması:**\n"
                    for i, (user_id, xp) in enumerate(sorted_users, 1):
                        member = kanal.guild.get_member(int(user_id))
                        isim = member.display_name if member else f"<@{user_id}>"
                        mesaj += f"**{i}.** {isim} — {xp} XP\n"

                    await kanal.send(mesaj)

                    # Haftalık veriyi sıfırla
                    self.weekly_levels[guild_id] = {}
                    self.save_weekly_data()

                await asyncio.sleep(60*60)  # 1 saat bekle tekrar atmaması için
            else:
                await asyncio.sleep(30)  # 30 saniyede bir kontrol et

async def setup(bot):
    await bot.add_cog(LevelSystem(bot))

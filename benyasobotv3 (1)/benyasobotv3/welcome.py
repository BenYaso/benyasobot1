import discord
from discord.ext import commands

WELCOME_CHANNEL_ID = 1385330706623893744  # Hoşgeldin mesajı kanalı ID'si
GOODBYE_CHANNEL_ID = 1385598733474992179  # Güle güle mesajı kanalı ID'si

class WelcomeGoodbye(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        kanal = self.bot.get_channel(WELCOME_CHANNEL_ID)
        if kanal:
            await kanal.send(f"🎉 Hoşgeldin {member.mention}! Aramıza katıldığın için çok mutluyuz! Kuralları okumayı unutma!")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        kanal = self.bot.get_channel(GOODBYE_CHANNEL_ID)
        if kanal:
            await kanal.send(f"😢 {member.name} aramızdan ayrıldı. Seni tekrar görmek isteriz!")

async def setup(bot):
    await bot.add_cog(WelcomeGoodbye(bot))
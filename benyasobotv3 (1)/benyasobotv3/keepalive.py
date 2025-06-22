from flask import Flask
import threading

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.daemon = True  # Thread’in bot kapanınca da kapanması için
    t.start()

# Eğer bu dosyayı bir cog olarak kullanacaksan:
async def setup(bot):
    keep_alive()

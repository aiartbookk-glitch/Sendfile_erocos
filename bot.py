import telebot
import requests
import base64
import uuid
from flask import Flask, request
import os

BOT_TOKEN = "8495788801:AAH52uGWsD-OUoTDdZlV6oy8NnyduVOmyos"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0Z19pZCI6NTMxMDU1NTUzNSwiZGJfbm0iOiJzdWJfZGF0YTIyIn0.lTMm5yAcPg0dgc3GPt-ECFxxL8iH0x1FDTYxreVr8pQ"

BASE_URL = "https://public-api.undresstool.fun/api/v1"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ================= TELEGRAM WEBHOOK =================

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200


# ================= CALLBACK TỪ API =================

@app.route("/api/callback", methods=["POST"])
def api_callback():
    data = request.json
    print("CALLBACK:", data)

    # bạn phải lưu mapping id_gen -> chat_id ở database
    # ví dụ demo gửi test về admin:

    admin_chat_id = 5310555535

    image_url = data.get("result")

    if image_url:
        img_data = requests.get(image_url).content
        bot.send_photo(admin_chat_id, img_data)

    return "OK", 200


# ================= HANDLE PHOTO =================

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.send_message(message.chat.id, "⏳ Đang xử lý...")

    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded = bot.download_file(file_info.file_path)

    encoded = base64.b64encode(downloaded).decode("utf-8")

    id_gen = str(uuid.uuid4())

    payload = {
        "id_gen": id_gen,
        "photo": encoded,
        "webhook": "https://your-railway-url.up.railway.app/api/callback"
    }

    response = requests.post(
        f"{BASE_URL}/photos/undress",
        headers={
            "X-API-KEY": API_KEY,
            "Content-Type": "application/json"
        },
        json=payload
    )

    print("CREATE:", response.status_code, response.text)


# ================= START SERVER =================

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"https://your-railway-url.up.railway.app/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

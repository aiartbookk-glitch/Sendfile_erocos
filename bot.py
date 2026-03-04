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

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        bot.send_message(message.chat.id, "⏳ Đang xử lý...")

        # tải ảnh
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)

        # convert base64
        encoded_photo = base64.b64encode(downloaded).decode("utf-8")

        payload = {
            "id_gen": str(uuid.uuid4()),   # random id
            "photo": encoded_photo,
            "webhook": "https://webhook.site/your-test-url"  # tạm test
        }

        response = requests.post(
            f"{BASE_URL}/photos/undress",
            headers={
                "X-API-KEY": API_KEY,
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=120
        )

        bot.send_message(message.chat.id, f"STATUS: {response.status_code}")
        bot.send_message(message.chat.id, response.text)

    except Exception as e:
        bot.send_message(message.chat.id, f"Lỗi: {str(e)}")

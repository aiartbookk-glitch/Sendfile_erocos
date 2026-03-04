import telebot
import requests
import io
import time

BOT_TOKEN = "8495788801:AAH52uGWsD-OUoTDdZlV6oy8NnyduVOmyos"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

BASE_URL = "https://public-api.undresstool.fun/api/v1"
CREATE_URL = f"{BASE_URL}/photos/undress"

bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "📸 Gửi ảnh để xử lý.")


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        bot.send_message(message.chat.id, "⏳ Đang xử lý...")

        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)

        image_file = io.BytesIO(downloaded)
        image_file.name = "image.jpg"

        # ✅ SỬA HEADER Ở ĐÂY
        response = requests.post(
            CREATE_URL,
            headers={"X-API-Key": API_KEY},
            files={"file": image_file},
            timeout=120
        )

        if response.status_code != 200:
            bot.send_message(message.chat.id, f"❌ API lỗi: {response.status_code}")
            bot.send_message(message.chat.id, response.text)
            return

        data = response.json()
        job_id = data.get("id")

        if not job_id:
            bot.send_message(message.chat.id, str(data))
            return

        for _ in range(30):
            check = requests.get(
                f"{BASE_URL}/photos/{job_id}",
                headers={"X-API-Key": API_KEY},
                timeout=60
            )

            result = check.json()

            if result.get("status") == "completed":
                image_url = result.get("result") or result.get("image")
                img_data = requests.get(image_url).content
                result_image = io.BytesIO(img_data)
                result_image.name = "result.jpg"
                bot.send_photo(message.chat.id, result_image)
                return

            if result.get("status") == "failed":
                bot.send_message(message.chat.id, "❌ Xử lý thất bại.")
                return

            time.sleep(2)

        bot.send_message(message.chat.id, "⌛ Hết thời gian chờ.")

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Lỗi: {str(e)}")


print("🚀 Bot đang chạy...")
bot.infinity_polling()

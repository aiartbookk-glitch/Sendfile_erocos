import telebot
import requests
import io

BOT_TOKEN = "8495788801:AAH52uGWsD-OUoTDdZlV6oy8NnyduVOmyos"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0Z19pZCI6NTMxMDU1NTUzNSwiZGJfbm0iOiJzdWJfZGF0YTIyIn0.lTMm5yAcPg0dgc3GPt-ECFxxL8iH0x1FDTYxreVr8pQ"

API_URL = "https://public-api.undresstool.fun/api/v1/photos/undress"

bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Gửi ảnh để xử lý.")


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        bot.send_message(message.chat.id, "⏳ Đang xử lý...")

        # tải ảnh từ Telegram
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)

        image_file = io.BytesIO(downloaded)
        image_file.name = "image.jpg"

        # gửi lên API
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}"
            },
            files={
                "file": image_file   # 👈 thường API dùng "file" thay vì "image"
            },
            timeout=300
        )

        if response.status_code != 200:
            bot.send_message(message.chat.id, f"❌ API lỗi: {response.status_code}")
            bot.send_message(message.chat.id, response.text)
            return

        data = response.json()

        # thường API trả job_id hoặc link ảnh
        image_url = data.get("result") or data.get("image") or data.get("url")

        if not image_url:
            bot.send_message(message.chat.id, "❌ Không tìm thấy ảnh trả về.")
            bot.send_message(message.chat.id, str(data))
            return

        img_data = requests.get(image_url).content
        result_image = io.BytesIO(img_data)
        result_image.name = "result.jpg"

        bot.send_photo(message.chat.id, result_image)

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Lỗi: {str(e)}")


print("Bot đang chạy...")
bot.infinity_polling()

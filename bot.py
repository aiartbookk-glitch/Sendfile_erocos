import telebot
import requests
import io
import time

BOT_TOKEN = "8495788801:AAH52uGWsD-OUoTDdZlV6oy8NnyduVOmyos"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0Z19pZCI6NTMxMDU1NTUzNSwiZGJfbm0iOiJzdWJfZGF0YTIyIn0.lTMm5yAcPg0dgc3GPt-ECFxxL8iH0x1FDTYxreVr8pQ"

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

        # === 1. Tải ảnh từ Telegram ===
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)

        image_file = io.BytesIO(downloaded)
        image_file.name = "image.jpg"

        # === 2. Gửi ảnh lên API tạo job ===
        response = requests.post(
            CREATE_URL,
            headers={"Authorization": f"Bearer {API_KEY}"},
            files={"file": image_file},
            timeout=120
        )

        if response.status_code != 200:
            bot.send_message(message.chat.id, f"❌ API lỗi: {response.status_code}")
            bot.send_message(message.chat.id, response.text)
            return

        data = response.json()
        print("CREATE RESPONSE:", data)

        job_id = data.get("id")

        if not job_id:
            bot.send_message(message.chat.id, "❌ Không nhận được job_id")
            bot.send_message(message.chat.id, str(data))
            return

        # === 3. Chờ xử lý xong ===
        for _ in range(30):  # tối đa ~60 giây
            check = requests.get(
                f"{BASE_URL}/photos/{job_id}",
                headers={"Authorization": f"Bearer {API_KEY}"},
                timeout=60
            )

            if check.status_code != 200:
                bot.send_message(message.chat.id, "❌ Lỗi khi kiểm tra trạng thái.")
                bot.send_message(message.chat.id, check.text)
                return

            result = check.json()
            print("CHECK RESPONSE:", result)

            status = result.get("status")

            if status == "completed":
                image_url = result.get("result") or result.get("image") or result.get("url")

                if not image_url:
                    bot.send_message(message.chat.id, "❌ Không tìm thấy link ảnh.")
                    bot.send_message(message.chat.id, str(result))
                    return

                img_data = requests.get(image_url).content
                result_image = io.BytesIO(img_data)
                result_image.name = "result.jpg"

                bot.send_photo(message.chat.id, result_image)
                return

            if status == "failed":
                bot.send_message(message.chat.id, "❌ Xử lý thất bại.")
                return

            time.sleep(2)

        bot.send_message(message.chat.id, "⌛ Hết thời gian chờ, thử lại sau.")

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Lỗi: {str(e)}")


print("🚀 Bot đang chạy...")
bot.infinity_polling()

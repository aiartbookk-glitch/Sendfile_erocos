import telebot
import requests
import io
import time

BOT_TOKEN = "8495788801:AAH52uGWsD-OUoTDdZlV6oy8NnyduVOmyos"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0Z19pZCI6NTMxMDU1NTUzNSwiZGJfbm0iOiJzdWJfZGF0YTIyIn0.lTMm5yAcPg0dgc3GPt-ECFxxL8iH0x1FDTYxreVr8pQ"   # <-- dán lại key cho chắc

BASE_URL = "https://public-api.undresstool.fun/api/v1"

bot = telebot.TeleBot(BOT_TOKEN)


# ================= TEST KEY KHI BOT CHẠY =================
def test_api_key():
    try:
        r = requests.get(
            f"{BASE_URL}/me",
            headers={"X-API-KEY": API_KEY},
            timeout=30
        )
        print("===== TEST AUTH =====")
        print("Status:", r.status_code)
        print("Response:", r.text)
        print("=====================")
    except Exception as e:
        print("Auth test error:", e)


test_api_key()


# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "📸 Gửi ảnh để xử lý.")


# ================= HANDLE PHOTO =================
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        bot.send_message(message.chat.id, "⏳ Đang xử lý...")

        # tải ảnh từ Telegram
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)

        image_file = io.BytesIO(downloaded)
        image_file.name = "image.jpg"

        # ====== TẠO JOB ======
        create = requests.post(
            f"{BASE_URL}/photos/undress",
            headers={"X-API-KEY": API_KEY},
            files={"file": image_file},
            timeout=120
        )

        print("CREATE STATUS:", create.status_code)
        print("CREATE RESPONSE:", create.text)

        if create.status_code != 200:
            bot.send_message(message.chat.id, f"❌ API lỗi: {create.status_code}")
            bot.send_message(message.chat.id, create.text)
            return

        data = create.json()
        job_id = data.get("id")

        if not job_id:
            bot.send_message(message.chat.id, "❌ Không nhận được job_id")
            bot.send_message(message.chat.id, str(data))
            return

        # ====== CHECK TRẠNG THÁI ======
        for _ in range(30):
            check = requests.get(
                f"{BASE_URL}/photos/{job_id}",
                headers={"X-API-KEY": API_KEY},
                timeout=60
            )

            print("CHECK STATUS:", check.status_code)
            print("CHECK RESPONSE:", check.text)

            if check.status_code != 200:
                bot.send_message(message.chat.id, "❌ Lỗi khi kiểm tra trạng thái.")
                bot.send_message(message.chat.id, check.text)
                return

            result = check.json()
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

        bot.send_message(message.chat.id, "⌛ Hết thời gian chờ.")

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Lỗi: {str(e)}")


print("🚀 Bot đang chạy...")
bot.infinity_polling()

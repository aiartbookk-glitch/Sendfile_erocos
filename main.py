import os
import requests
from fastapi import FastAPI, UploadFile, File, Form
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

app = FastAPI()

# ===== CONFIG =====
BOT_TOKEN = "8751204704:AAHVLFWRt1hQvz3HxnwDNt7IRhA4eZYEfjg"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0Z19pZCI6NTMxMDU1NTUzNSwiZGJfbm0iOiJzdWJfZGF0YTgzIn0.icegufzG28O8T99fy_dawALjVlDSTbo62RCTnIRUk1k"
WEBHOOK_URL = "https://librariannudebot-production.up.railway.app/"

bot = Bot(token=BOT_TOKEN)

# lưu job_id -> chat_id
JOB_MAP = {}

# ===== TELEGRAM BOT =====
tg_app = ApplicationBuilder().token(BOT_TOKEN).build()


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Đang xử lý ảnh...")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    path = await file.download_to_drive()

    # gửi API
    with open(path, "rb") as f:
        res = requests.post(
            "https://public-api.undresstool.fun/api/v1/photos/undress",
            headers={"Authorization": f"Bearer {API_KEY}"},
            files={"file": f},
            data={
                "webhook_url": f"{WEBHOOK_URL}/undress-photo-webhook"
            }
        )

    data = res.json()
    print("API response:", data)

    job_id = data.get("id") or data.get("job_id")

    if not job_id:
        await update.message.reply_text("API lỗi, thử lại sau")
        return

    JOB_MAP[job_id] = update.message.chat_id


tg_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))


# ===== START BOT (CHUẨN ASYNC) =====
@app.on_event("startup")
async def startup():
    await tg_app.initialize()
    await tg_app.start()
    tg_app.create_task(tg_app.run_polling())


@app.on_event("shutdown")
async def shutdown():
    await tg_app.stop()
    await tg_app.shutdown()


# ===== WEBHOOK NHẬN KẾT QUẢ =====
@app.post("/undress-photo-webhook")
async def webhook(
    status: str = Form(...),
    id_gen: str = Form(...),
    res_image: UploadFile = File(...)
):
    print("Webhook hit:", id_gen)

    chat_id = JOB_MAP.get(id_gen)

    if not chat_id:
        print("Không tìm thấy chat_id")
        return {"error": "no chat_id"}

    file_path = f"/tmp/{id_gen}.png"

    with open(file_path, "wb") as f:
        f.write(await res_image.read())

    await bot.send_photo(chat_id=chat_id, photo=open(file_path, "rb"))

    return {"ok": True}


# ===== TEST =====
@app.get("/")
async def root():
    return {"status": "running"}

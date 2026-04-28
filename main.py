import os
import requests
from fastapi import FastAPI, UploadFile, File, Form
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import asyncio

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")

bot = Bot(token=BOT_TOKEN)

# lưu job_id -> chat_id
JOB_MAP = {}

# ================= TELEGRAM BOT =================

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Đang xử lý ảnh...")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    path = await file.download_to_drive()

    # gửi lên API
    with open(path, "rb") as f:
        res = requests.post(
            "https://public-api.undresstool.fun/api/v1/photos/undress",
            headers={"Authorization": f"Bearer {API_KEY}"},
            files={"file": f},
            data={
                "webhook_url": os.getenv("WEBHOOK_URL") + "/undress-photo-webhook"
            }
        )

    data = res.json()
    job_id = data.get("id") or data.get("job_id")

    JOB_MAP[job_id] = update.message.chat_id


def start_bot():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app_bot.run_polling()

# chạy bot song song
@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_event_loop()
    loop.create_task(asyncio.to_thread(start_bot))


# ================= WEBHOOK =================

@app.post("/undress-photo-webhook")
async def webhook(
    status: str = Form(...),
    id_gen: str = Form(...),
    res_image: UploadFile = File(...)
):
    chat_id = JOB_MAP.get(id_gen)

    if not chat_id:
        return {"error": "no chat_id"}

    file_path = f"temp_{id_gen}.png"

    with open(file_path, "wb") as f:
        f.write(await res_image.read())

    await bot.send_photo(chat_id=chat_id, photo=open(file_path, "rb"))

    return {"ok": True}


@app.get("/")
async def root():
    return {"status": "running"}

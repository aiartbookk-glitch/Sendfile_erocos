import os
import requests
from fastapi import FastAPI, Request, UploadFile, File, Form
from telegram import Update, Bot

app = FastAPI()

BOT_TOKEN = "8751204704:AAHVLFWRt1hQvz3HxnwDNt7IRhA4eZYEfjg"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0Z19pZCI6NTMxMDU1NTUzNSwiZGJfbm0iOiJzdWJfZGF0YTgzIn0.icegufzG28O8T99fy_dawALjVlDSTbo62RCTnIRUk1k"
WEBHOOK_URL = "https://librariannudebot-production.up.railway.app/"

bot = Bot(token=BOT_TOKEN)

JOB_MAP = {}

# ===== TELEGRAM WEBHOOK =====
@app.post(f"/telegram/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)

    if update.message and update.message.photo:
        chat_id = update.message.chat_id

        await bot.send_message(chat_id, "Đang xử lý ảnh...")

        photo = update.message.photo[-1]
        file = await bot.get_file(photo.file_id)
        path = await file.download_to_drive()

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
        print("API:", data)

        job_id = data.get("id") or data.get("job_id")

        if job_id:
            JOB_MAP[job_id] = chat_id
        else:
            await bot.send_message(chat_id, "API lỗi")

    return {"ok": True}


# ===== NHẬN KẾT QUẢ TỪ API =====
@app.post("/undress-photo-webhook")
async def result_webhook(
    status: str = Form(...),
    id_gen: str = Form(...),
    res_image: UploadFile = File(...)
):
    print("Webhook:", id_gen)

    chat_id = JOB_MAP.get(id_gen)

    if not chat_id:
        return {"error": "no chat_id"}

    path = f"/tmp/{id_gen}.png"

    with open(path, "wb") as f:
        f.write(await res_image.read())

    await bot.send_photo(chat_id=chat_id, photo=open(path, "rb"))

    return {"ok": True}


# ===== SET TELEGRAM WEBHOOK =====
@app.on_event("startup")
async def setup_webhook():
    url = f"{WEBHOOK_URL}/telegram/{BOT_TOKEN}"
    await bot.set_webhook(url)
    print("Webhook set:", url)


@app.get("/")
async def root():
    return {"status": "running"}

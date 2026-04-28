import os
import uuid
import requests
from fastapi import FastAPI, Request, UploadFile, File
from telegram import Update, Bot

app = FastAPI()

# ===== CONFIG =====
BOT_TOKEN = "8751204704:AAHVLFWRt1hQvz3HxnwDNt7IRhA4eZYEfjg"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0Z19pZCI6NTMxMDU1NTUzNSwiZGJfbm0iOiJzdWJfZGF0YTgzIn0.icegufzG28O8T99fy_dawALjVlDSTbo62RCTnIRUk1k"
WEBHOOK_URL = "https://librariannudebot-production.up.railway.app"

bot = Bot(token=BOT_TOKEN)

# lưu job tạm (nên thay bằng Redis/DB nếu production)
JOB_MAP = {}


# =========================
# TELEGRAM WEBHOOK
# =========================
@app.post(f"/telegram/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)

    if not update.message:
        return {"ok": True}

    chat_id = update.message.chat_id

    # ===== GET FILE ID =====
    file_id = None

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    else:
        await bot.send_message(chat_id, "Gửi ảnh đi.")
        return {"ok": True}

    await bot.send_message(chat_id, "Đang xử lý...")

    # ===== DOWNLOAD FILE =====
    tg_file = await bot.get_file(file_id)

    input_path = f"/tmp/{file_id}.jpg"
    await tg_file.download_to_drive(input_path)

    # ===== CALL EXTERNAL API (PLACEHOLDER) =====
    job_id = str(uuid.uuid4())

    try:
        with open(input_path, "rb") as f:
            res = requests.post(
                "https://example-api.com/process",  # <-- thay API của bạn
                headers={
                    "X-API-KEY": API_KEY
                },
                files={
                    "file": f
                },
                data={
                    "job_id": job_id,
                    "webhook": f"{WEBHOOK_URL}/result-webhook"
                },
                timeout=60
            )

        print("API STATUS:", res.status_code)
        print("API RESPONSE:", res.text)

    except Exception as e:
        print("API ERROR:", e)
        await bot.send_message(chat_id, "Lỗi xử lý API")
        return {"ok": True}

    if res.status_code != 200:
        await bot.send_message(chat_id, f"API lỗi: {res.text}")
        return {"ok": True}

    # save mapping
    JOB_MAP[job_id] = chat_id
    print("JOB_MAP:", JOB_MAP)

    return {"ok": True}


# =========================
# RESULT WEBHOOK (FIX 422)
# =========================
@app.post("/result-webhook")
async def result_webhook(request: Request):
    """
    FIX 422:
    Không ép schema Form/File nữa → đọc raw form an toàn
    """
    form = await request.form()

    print("=== CALLBACK RECEIVED ===")
    print("FORM KEYS:", list(form.keys()))

    job_id = form.get("job_id")
    status = form.get("status")

    # file có thể tên khác nhau tùy API
    file_obj = None
    for k, v in form.items():
        if hasattr(v, "file"):
            file_obj = v
            break

    if not job_id:
        return {"error": "missing job_id"}

    chat_id = JOB_MAP.get(job_id)

    if not chat_id:
        print("Missing chat_id (maybe restart server)")
        return {"error": "no chat_id"}

    # ===== SAVE RESULT FILE =====
    output_path = f"/tmp/result_{job_id}.bin"

    if file_obj:
        with open(output_path, "wb") as f:
            f.write(await file_obj.read())

        await bot.send_photo(chat_id=chat_id, photo=open(output_path, "rb"))
    else:
        await bot.send_message(chat_id, f"Done but no file. Status: {status}")

    return {"ok": True}


# =========================
# SET WEBHOOK ON STARTUP
# =========================
@app.on_event("startup")
async def startup():
    url = f"{WEBHOOK_URL}/telegram/{BOT_TOKEN}"
    await bot.set_webhook(url)
    print("Webhook set:", url)


@app.get("/")
async def root():
    return {"status": "running"}

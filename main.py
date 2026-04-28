import uuid
import requests
from fastapi import FastAPI, Request
from telegram import Update, Bot

app = FastAPI()

# ===== CONFIG =====
BOT_TOKEN = "8751204704:AAHVLFWRt1hQvz3HxnwDNt7IRhA4eZYEfjg"
API_URL = "https://public-api.undresstool.fun/docs#/Photo/undress_api_v1_photos_undress_post"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0Z19pZCI6NTMxMDU1NTUzNSwiZGJfbm0iOiJzdWJfZGF0YTgzIn0.icegufzG28O8T99fy_dawALjVlDSTbo62RCTnIRUk1k"
WEBHOOK_URL = "https://librariannudebot-production.up.railway.app"

bot = Bot(token=BOT_TOKEN)

# memory (dev only)
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

    file_id = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    else:
        await bot.send_message(chat_id, "Gửi ảnh đi.")
        return {"ok": True}

    await bot.send_message(chat_id, "Đang xử lý...")

    tg_file = await bot.get_file(file_id)
    input_path = f"/tmp/{file_id}.jpg"
    await tg_file.download_to_drive(input_path)

    job_id = str(uuid.uuid4())

    # ================= CALL API SAFE =================
    try:
        with open(input_path, "rb") as f:

            payload = {
                "id_gen": job_id,
                "webhook": f"{WEBHOOK_URL}/result-webhook"
            }

            files = {
                "photo": ("image.jpg", f, "image/jpeg")
            }

            headers = {
                "X-API-KEY": API_KEY
            }

            res = requests.post(
                API_URL,
                data=payload,
                files=files,
                headers=headers,
                timeout=120
            )

        print("API STATUS:", res.status_code)
        print("API RESPONSE:", res.text)

    except Exception as e:
        print("API ERROR:", e)
        await bot.send_message(chat_id, "Lỗi API (network/timeout)")
        return {"ok": True}

    # ===== NEVER FAIL BOT EVEN IF API FAILS =====
    if res.status_code != 200:
        await bot.send_message(chat_id, "API lỗi, thử lại sau.")
        return {"ok": True}

    JOB_MAP[job_id] = chat_id

    return {"ok": True}


# =========================
# RESULT WEBHOOK (ANTI-422 SAFE)
# =========================
@app.post("/result-webhook")
async def result_webhook(request: Request):

    try:
        form = await request.form()
    except Exception as e:
        print("FORM ERROR:", e)
        return {"ok": True}

    print("WEBHOOK KEYS:", list(form.keys()))

    # flexible id parsing
    job_id = (
        form.get("id_gen")
        or form.get("job_id")
        or form.get("id")
    )

    if not job_id:
        return {"ok": True}

    chat_id = JOB_MAP.get(job_id)

    if not chat_id:
        print("Missing chat_id (restart or unknown job)")
        return {"ok": True}

    file_obj = None
    for v in form.values():
        if hasattr(v, "file"):
            file_obj = v
            break

    output_path = f"/tmp/result_{job_id}.jpg"

    if file_obj:
        with open(output_path, "wb") as f:
            f.write(await file_obj.read())

        await bot.send_photo(chat_id, open(output_path, "rb"))
    else:
        await bot.send_message(chat_id, "Done nhưng không có file")

    return {"ok": True}


# =========================
# STARTUP
# =========================
@app.on_event("startup")
async def startup():
    url = f"{WEBHOOK_URL}/telegram/{BOT_TOKEN}"
    await bot.set_webhook(url)
    print("Webhook set:", url)


@app.get("/")
async def root():
    return {"status": "ok"}

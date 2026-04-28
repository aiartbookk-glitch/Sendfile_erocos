import base64
import uuid
import requests
from fastapi import FastAPI, Request, UploadFile, File, Form
from telegram import Update, Bot

app = FastAPI()

# ===== CONFIG =====
BOT_TOKEN = "8751204704:AAHVLFWRt1hQvz3HxnwDNt7IRhA4eZYEfjg"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0Z19pZCI6NTMxMDU1NTUzNSwiZGJfbm0iOiJzdWJfZGF0YTgzIn0.icegufzG28O8T99fy_dawALjVlDSTbo62RCTnIRUk1k"
WEBHOOK_URL = "https://librariannudebot-production.up.railway.app"

bot = Bot(token=BOT_TOKEN)

# lưu id_gen -> chat_id
JOB_MAP = {}

# ===== TELEGRAM WEBHOOK =====
@app.post(f"/telegram/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    data = await request.json()
    print("UPDATE RAW:", data)

    update = Update.de_json(data, bot)

    if not update.message:
        return {"ok": True}

    chat_id = update.message.chat_id

    # ===== LẤY ẢNH =====
    file_id = None

    if update.message.photo:
        print("Nhận ảnh dạng photo")
        file_id = update.message.photo[-1].file_id

    elif update.message.document:
        print("Nhận ảnh dạng document")
        file_id = update.message.document.file_id

    else:
        await bot.send_message(chat_id, "Gửi ảnh đi")
        return {"ok": True}

    await bot.send_message(chat_id, "Đang xử lý ảnh...")

    # ===== DOWNLOAD ẢNH =====
    file = await bot.get_file(file_id)
    path = f"/tmp/{file_id}.jpg"
    await file.download_to_drive(path)

    # ===== CHUYỂN BASE64 =====
    with open(path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    id_gen = str(uuid.uuid4())

    # ===== GỬI API (FIX ĐÚNG FORM-DATA) =====
    try:
        res = requests.post(
            "https://public-api.undresstool.fun/api/v1/photos/undress",
            headers={
                "X-API-KEY": API_KEY
            },
            data={  # ⚠️ QUAN TRỌNG: dùng data=, không phải json=
                "id_gen": id_gen,
                "photo": img_b64,
                "webhook": f"{WEBHOOK_URL}/undress-photo-webhook"
            }
        )

        print("STATUS:", res.status_code)
        print("API RESPONSE:", res.text)

        data_api = res.json()

    except Exception as e:
        print("API ERROR:", e)
        await bot.send_message(chat_id, "Lỗi API")
        return {"ok": True}

    if res.status_code != 200:
        await bot.send_message(chat_id, "API lỗi")
        return {"ok": True}

    # lưu mapping
    JOB_MAP[id_gen] = chat_id
    print("JOB_MAP:", JOB_MAP)

    return {"ok": True}


# ===== NHẬN KẾT QUẢ TỪ API =====
@app.post("/undress-photo-webhook")
async def result_webhook(
    status: str = Form(...),
    id_gen: str = Form(...),
    res_image: UploadFile = File(...)
):
    print("WEBHOOK RESULT:", id_gen)

    chat_id = JOB_MAP.get(id_gen)

    if not chat_id:
        print("Không tìm thấy chat_id (có thể Railway restart)")
        return {"error": "no chat_id"}

    path = f"/tmp/result_{id_gen}.png"

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

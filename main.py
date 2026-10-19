import os
import uuid
import json
import logging
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, Form, Request, HTTPException, Header
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import httpx
import aiofiles

# ============== CONFIG ==============
UNDRESS_API_KEY = os.getenv("UNDRESS_API_KEY", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
UNDRESS_BASE = "https://public-api.undresstool.fun"
WEBHOOK_PATH = "/webhook"

# In-memory storage (restart = mất dữ liệu)
results: dict = {}
pending: dict = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Undress Webhook Server")


# ============== HELPERS ==============
def get_public_url(request: Request) -> str:
    """Lấy public URL của service (Railway set header này)."""
    proto = request.headers.get("x-forwarded-proto", "https")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    return f"{proto}://{host}"


async def call_undress_api(
    photo_bytes: bytes,
    filename: str,
    id_gen: str,
    webhook_url: str,
    cloth: Optional[str] = None,
    age: Optional[str] = None,
    breast_size: Optional[str] = None,
    body_type: Optional[str] = None,
    butt_size: Optional[str] = None,
    post_gen: Optional[str] = None,
) -> dict:
    """Gọi Undress API."""
    if not UNDRESS_API_KEY:
        raise HTTPException(status_code=500, detail="UNDRESS_API_KEY chưa được set")

    url = f"{UNDRESS_BASE}/api/v1/photos/undress"
    headers = {"X-API-KEY": UNDRESS_API_KEY}

    files = {"photo": (filename, photo_bytes, "image/jpeg")}
    data = {
        "id_gen": id_gen,
        "webhook": webhook_url,
    }
    if cloth:
        data["cloth"] = cloth
    if age:
        data["age"] = age
    if breast_size:
        data["breast_size"] = breast_size
    if body_type:
        data["body_type"] = body_type
    if butt_size:
        data["butt_size"] = butt_size
    if post_gen:
        data["post_gen"] = post_gen

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, files=files, data=data)
        try:
            return resp.json()
        except Exception:
            return {"status": "error", "raw": resp.text, "code": resp.status_code}


# ============== ENDPOINTS ==============
@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Undress Tool</h1><p>index.html not found</p>"


@app.get("/me")
async def get_me():
    """Kiểm tra balance Undress API."""
    if not UNDRESS_API_KEY:
        raise HTTPException(status_code=500, detail="UNDRESS_API_KEY chưa được set")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{UNDRESS_BASE}/api/v1/me",
            headers={"X-API-KEY": UNDRESS_API_KEY},
        )
        return resp.json()


@app.post("/upload")
async def upload_photo(
    request: Request,
    photo: UploadFile = File(...),
    cloth: Optional[str] = Form(None),
    age: Optional[str] = Form(None),
    breast_size: Optional[str] = Form(None),
    body_type: Optional[str] = Form(None),
    butt_size: Optional[str] = Form(None),
    post_gen: Optional[str] = Form(None),
):
    """
    Upload ảnh từ local và tự động gọi Undress API.
    Trả về id_gen để theo dõi kết quả.
    """
    photo_bytes = await photo.read()
    if not photo_bytes:
        raise HTTPException(status_code=400, detail="File ảnh trống")

    id_gen = str(uuid.uuid4())
    public_url = get_public_url(request)
    webhook_url = f"{public_url}{WEBHOOK_PATH}"

    logger.info(f"Upload: id_gen={id_gen}, webhook={webhook_url}")

    pending[id_gen] = {
        "created_at": datetime.utcnow().isoformat(),
        "filename": photo.filename,
        "status": "pending",
    }

    result = await call_undress_api(
        photo_bytes=photo_bytes,
        filename=photo.filename or "photo.jpg",
        id_gen=id_gen,
        webhook_url=webhook_url,
        cloth=cloth,
        age=age,
        breast_size=breast_size,
        body_type=body_type,
        butt_size=butt_size,
        post_gen=post_gen,
    )

    pending[id_gen]["api_response"] = result

    return {
        "id_gen": id_gen,
        "webhook": webhook_url,
        "api_response": result,
        "check_result": f"/result/{id_gen}",
    }


@app.post("/webhook")
async def webhook(request: Request):
    """Nhận kết quả từ Undress API (multipart/form-data)."""
    try:
        form = await request.form()
        data = {key: form[key] for key in form.keys()}
        
        # Nếu có file ảnh thì lấy URL hoặc bytes
        if "image" in form and hasattr(form["image"], "file"):
            # Có thể là file upload
            pass
        
        id_gen = data.get("id_gen")
        image_url = data.get("image_url") or data.get("result") or data.get("url")
        
        logger.info(f"Webhook received: id_gen={id_gen}, image_url={image_url}")
        logger.info(f"Full form data: {data}")

        if id_gen:
            results[id_gen] = {
                "received_at": datetime.utcnow().isoformat(),
                "id_gen": id_gen,
                "image_url": image_url,
                "payload": data,
            }
            if id_gen in pending:
                pending[id_gen]["status"] = "done"

        return {"ok": True, "id_gen": id_gen}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        # Fallback: thử đọc raw body
        body = await request.body()
        logger.info(f"Raw body: {body[:1000]}")
        return {"ok": False, "error": str(e)}


@app.get("/result/{id_gen}")
async def get_result(id_gen: str):
    """Lấy kết quả theo id_gen."""
    result = results.get(id_gen)
    pending_info = pending.get(id_gen)

    if result:
        return {"status": "done", "id_gen": id_gen, **result}
    if pending_info:
        return {"status": "pending", "id_gen": id_gen, **pending_info}
    raise HTTPException(status_code=404, detail="Không tìm thấy id_gen")


@app.get("/list")
async def list_all():
    """Liệt kê tất cả pending và results (debug)."""
    return {
        "pending": pending,
        "results": {k: {"received_at": v.get("received_at")} for k, v in results.items()},
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

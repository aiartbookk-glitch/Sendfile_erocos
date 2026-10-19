import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

import aiosqlite
import httpx
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

load_dotenv()

# ============== CONFIG ==============
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
UNDRESS_API_KEY = os.getenv("UNDRESS_API_KEY", "")
WEBHOOK_SERVER = os.getenv("WEBHOOK_SERVER", "https://sendfileerocos-production.up.railway.app")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

INITIAL_CREDITS = int(os.getenv("INITIAL_CREDITS", "1"))
REF_REWARD = int(os.getenv("REF_REWARD", "2"))
NEW_USER_BONUS = int(os.getenv("NEW_USER_BONUS", "3"))
PHOTO_COST = int(os.getenv("PHOTO_COST", "2"))
CUSTOM_PHOTO_COST = int(os.getenv("CUSTOM_PHOTO_COST", "3"))

DB_PATH = "bot.db"
UNDRESS_BASE = "https://public-api.undresstool.fun"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)


# ============== DATABASE ==============
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                credits INTEGER DEFAULT 0,
                referred_by INTEGER,
                created_at TEXT,
                total_generated INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER UNIQUE,
                rewarded INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id_gen TEXT PRIMARY KEY,
                telegram_id INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                image_url TEXT
            )
        """)
        await db.commit()


async def get_user(telegram_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def create_user(telegram_id: int, username: str, referred_by: Optional[int] = None) -> dict:
    credits = INITIAL_CREDITS
    if referred_by and referred_by != telegram_id:
        credits += NEW_USER_BONUS

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (telegram_id, username, credits, referred_by, created_at) VALUES (?, ?, ?, ?, ?)",
            (telegram_id, username, credits, referred_by, datetime.utcnow().isoformat()),
        )
        if referred_by and referred_by != telegram_id:
            await db.execute(
                "INSERT OR IGNORE INTO referrals (referrer_id, referred_id, created_at) VALUES (?, ?, ?)",
                (referred_by, telegram_id, datetime.utcnow().isoformat()),
            )
        await db.commit()
    return await get_user(telegram_id)


async def add_credits(telegram_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET credits = credits + ? WHERE telegram_id = ?", (amount, telegram_id))
        await db.commit()


async def deduct_credits(telegram_id: int, amount: int) -> bool:
    user = await get_user(telegram_id)
    if not user or user["credits"] < amount:
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET credits = credits - ?, total_generated = total_generated + 1 WHERE telegram_id = ?", (amount, telegram_id))
        await db.commit()
    return True


async def reward_referrer(referred_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT referrer_id FROM referrals WHERE referred_id = ? AND rewarded = 0", (referred_id,)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return
            referrer_id = row["referrer_id"]
            await db.execute("UPDATE referrals SET rewarded = 1 WHERE referred_id = ?", (referred_id,))
            await db.execute("UPDATE users SET credits = credits + ? WHERE telegram_id = ?", (REF_REWARD, referrer_id))
            await db.commit()
            try:
                await bot.send_message(referrer_id, f"🎉 Bạn nhận được +{REF_REWARD} credit từ referral!")
            except Exception:
                pass


async def save_task(id_gen: str, telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO tasks (id_gen, telegram_id, status, created_at) VALUES (?, ?, 'pending', ?)",
            (id_gen, telegram_id, datetime.utcnow().isoformat()),
        )
        await db.commit()


async def update_task(id_gen: str, status: str, image_url: Optional[str] = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE tasks SET status = ?, image_url = ? WHERE id_gen = ?",
            (status, image_url, id_gen),
        )
        await db.commit()


async def get_task(id_gen: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tasks WHERE id_gen = ?", (id_gen,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


# ============== HELPERS ==============
def get_ref_link(telegram_id: int) -> str:
    return f"https://t.me/{(bot.username or 'YourBot')}?start=ref_{telegram_id}"


async def call_undress(photo_bytes: bytes, filename: str, id_gen: str, cloth: Optional[str] = None, age: Optional[str] = None) -> dict:
    webhook_url = f"{WEBHOOK_SERVER}/webhook"
    url = f"{UNDRESS_BASE}/api/v1/photos/undress"
    headers = {"X-API-KEY": UNDRESS_API_KEY}
    files = {"photo": (filename, photo_bytes, "image/jpeg")}
    data = {"id_gen": id_gen, "webhook": webhook_url}
    if cloth:
        data["cloth"] = cloth
    if age:
        data["age"] = age

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, files=files, data=data)
        return resp.json()


# ============== HANDLERS ==============
@router.message(CommandStart())
async def cmd_start(message: Message):
    args = message.text.split(maxsplit=1)
    referred_by = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referred_by = int(args[1][4:])
        except ValueError:
            pass

    user = await get_user(message.from_user.id)
    if not user:
        user = await create_user(message.from_user.id, message.from_user.username or "", referred_by)

    ref_link = get_ref_link(message.from_user.id)
    text = (
        f"👋 Xin chào {message.from_user.first_name}!\n\n"
        f"💰 Credit: <b>{user['credits']}</b>\n"
        f"🖼 Đã tạo: {user['total_generated']}\n\n"
        f"📎 Link giới thiệu của bạn:\n<code>{ref_link}</code>\n\n"
        f"Giới thiệu bạn bè để nhận <b>+{REF_REWARD} credit</b> mỗi người dùng thành công.\n"
        f"Gửi ảnh để bắt đầu (chi phí: {PHOTO_COST} credit)."
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("balance"))
async def cmd_balance(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Bạn chưa đăng ký. Gõ /start")
        return
    await message.answer(f"💰 Credit hiện tại: <b>{user['credits']}</b>", parse_mode="HTML")


@router.message(Command("ref"))
async def cmd_ref(message: Message):
    link = get_ref_link(message.from_user.id)
    await message.answer(
        f"📎 Link giới thiệu:\n<code>{link}</code>\n\n"
        f"Mỗi người bạn giới thiệu dùng bot thành công → bạn nhận <b>+{REF_REWARD} credit</b>.",
        parse_mode="HTML",
    )


@router.message(Command("addcredit"))
async def cmd_addcredit(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Dùng: /addcredit <telegram_id> <số_credit>")
        return
    try:
        target_id = int(parts[1])
        amount = int(parts[2])
        await add_credits(target_id, amount)
        await message.answer(f"✅ Đã cộng {amount} credit cho {target_id}")
        try:
            await bot.send_message(target_id, f"💰 Admin đã cộng <b>{amount}</b> credit cho bạn!", parse_mode="HTML")
        except Exception:
            pass
    except Exception as e:
        await message.answer(f"Lỗi: {e}")


@router.message(F.photo)
async def handle_photo(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Gõ /start trước.")
        return

    cost = PHOTO_COST
    if user["credits"] < cost:
        await message.answer(f"❌ Không đủ credit. Cần {cost}, bạn có {user['credits']}.\nDùng /ref để kiếm thêm.")
        return

    if not await deduct_credits(message.from_user.id, cost):
        await message.answer("❌ Trừ credit thất bại.")
        return

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)
    photo_data = file_bytes.read()

    id_gen = str(uuid.uuid4())
    await save_task(id_gen, message.from_user.id)

    await message.answer("⏳ Đang xử lý... Kết quả sẽ gửi sau.")

    try:
        result = await call_undress(photo_data, "photo.jpg", id_gen)
        if result.get("status") != "success":
            await add_credits(message.from_user.id, cost)
            await message.answer(f"❌ Lỗi API: {result}")
            return
    except Exception as e:
        await add_credits(message.from_user.id, cost)
        await message.answer(f"❌ Lỗi: {e}")
        return

    # Poll kết quả từ webhook server
    for _ in range(60):
        await asyncio.sleep(2)
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"{WEBHOOK_SERVER}/result/{id_gen}")
                data = resp.json()
                if data.get("status") == "done" and data.get("image_url"):
                    await update_task(id_gen, "done", data["image_url"])
                    await message.answer_photo(data["image_url"], caption="✅ Xong!")
                    await reward_referrer(message.from_user.id)
                    return
        except Exception:
            pass

    await add_credits(message.from_user.id, cost)
    await message.answer("❌ Hết thời gian chờ. Credit đã được hoàn lại.")


# ============== MAIN ==============
async def main():
    await init_db()
    me = await bot.get_me()
    bot.username = me.username
    logger.info(f"Bot started: @{me.username}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

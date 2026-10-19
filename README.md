# Undress Telegram Bot (Credit + Referral)

Bot Telegram tích hợp Undress API, hệ thống credit và referral.

## Tính năng

- Credit system
- Referral (kiếm credit khi giới thiệu)
- Gửi ảnh → nhận kết quả undress
- Admin nạp credit (`/addcredit`)
- Tích hợp webhook server Railway đã có

## Cài đặt

1. Copy `.env.example` thành `.env` và điền:
   - `BOT_TOKEN` (từ @BotFather)
   - `UNDRESS_API_KEY`
   - `WEBHOOK_SERVER` (URL Railway của bạn)
   - `ADMIN_IDS` (telegram_id của admin, cách nhau bởi dấu phẩy)

2. Cài dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Chạy:
   ```bash
   python bot.py
   ```

## Deploy

Có thể chạy trên Railway, VPS, hoặc máy local (polling).

## Lệnh

| Lệnh | Mô tả |
|------|------|
| `/start` | Đăng ký / xem credit |
| `/balance` | Xem số credit |
| `/ref` | Lấy link giới thiệu |
| `/addcredit <id> <số>` | Admin cộng credit |

## Cơ chế Ref

- Người mới join qua link ref nhận **+3 credit** bonus
- Khi người mới tạo ảnh thành công lần đầu → người giới thiệu nhận **+2 credit**
- Mỗi người chỉ được thưởng 1 lần

## Chi phí

- Ảnh thường: 2 credit
- Có tùy chỉnh (cloth, age...): 3 credit (có thể mở rộng trong code)

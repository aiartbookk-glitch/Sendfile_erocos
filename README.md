# Undress Webhook Server (Railway + GitHub)

Server nhận webhook từ Undress API và cung cấp endpoint upload ảnh đơn giản.

## Tính năng

- Endpoint `/webhook` nhận kết quả từ Undress API
- Endpoint `/upload` nhận ảnh từ local và tự động gọi Undress API
- Endpoint `/result/{id_gen}` kiểm tra kết quả
- Lưu kết quả tạm thời trong memory (restart sẽ mất)

## Deploy lên Railway

1. Push repo này lên GitHub
2. Vào [Railway](https://railway.app) → New Project → Deploy from GitHub repo
3. Thêm biến môi trường:
   - `UNDRESS_API_KEY`: API key của bạn
   - `WEBHOOK_SECRET` (tuỳ chọn): secret để bảo vệ webhook
4. Railway sẽ cho URL public, ví dụ: `https://xxx.up.railway.app`

## Sử dụng

### Upload ảnh từ máy local

```bash
curl -X POST "https://YOUR-RAILWAY-URL/upload" \
  -F "photo=@/path/to/photo.jpg" \
  -F "cloth=Naked" \
  -F "age=20"
```

Trả về `id_gen`. Sau đó kiểm tra kết quả:

```bash
curl "https://YOUR-RAILWAY-URL/result/YOUR_ID_GEN"
```

### Kiểm tra balance

```bash
curl "https://YOUR-RAILWAY-URL/me"
```

## Biến môi trường

| Biến | Bắt buộc | Mô tả |
|------|----------|-------|
| `UNDRESS_API_KEY` | Có | API key Undress |
| `WEBHOOK_SECRET` | Không | Secret header bảo vệ webhook |
| `PORT` | Không | Railway tự set |

## Lưu ý

- Chỉ sử dụng với ảnh người lớn (≥18) và có sự đồng ý rõ ràng.
- Kết quả lưu trong memory, restart app sẽ mất. Nên nâng cấp lên Redis/S3 nếu dùng lâu dài.
- Rate limit Undress API: 60 request/phút khi có key.

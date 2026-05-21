# ❤️ For Our Relationship

Web app cho các cặp đôi — **mỗi ngày một câu hỏi chung**, cả hai cùng trả lời riêng,
cuối ngày mở ra xem câu trả lời của nhau. Giao diện mobile-friendly, ấm áp.

---

## Cách hoạt động

1. 🌅 **Mỗi sáng** mở app → có popup chào buổi sáng + câu hỏi mới của ngày
2. ✍️ **Mỗi người trả lời riêng** — không thấy câu của người kia
3. ⏳ Trả lời xong thì **chờ** người còn lại
4. 🎁 Khi **cả hai đã trả lời** → nhấn "Mở câu trả lời của nhau" để cùng reveal
5. 💌 Tab **Kỷ niệm** lưu lại tất cả câu hỏi & câu trả lời của những ngày đã qua

Mỗi điện thoại chỉ cần **chọn vai (Người 1 / Người 2) + nhập tên** một lần.

## Tính năng

- 📅 Câu hỏi mỗi ngày, chung cho cả hai (không trùng lặp — 80 câu, 10 chủ đề)
- ✍️ Trả lời riêng tư, ẩn cho tới khi cả hai xong
- 🎁 Cùng reveal câu trả lời
- 🌅 Popup chào buổi sáng khi có câu mới
- 💌 Lịch sử "Kỷ niệm" các ngày đã qua
- 📱 Mobile-first, floating hearts, theme hồng ấm

## Cài đặt & Chạy

```bash
pip install -r requirements.txt
python app.py
```

- Máy tính: `http://localhost:5000`
- Điện thoại (cùng WiFi): app in ra địa chỉ IP khi khởi động — mở trên cả 2 điện thoại

> 💡 Để cả hai dùng từ xa (khác mạng), deploy lên một host như Render/Railway/PythonAnywhere
> hoặc dùng tunnel (ngrok). State lưu trong `state.json` trên server chung.

## 🔔 Thông báo đẩy (Web Push)

App là một **PWA** — thêm vào màn hình chính điện thoại để dùng như app thật.

- App **hỏi quyền thông báo trước** (banner "Bật nhắc nhở mỗi sáng?")
- Sau khi cho phép → nhận push: **mỗi sáng** có câu hỏi mới, và **khi người ấy đã trả lời**
- Thông báo tự bật **kể cả khi không mở app** (qua service worker)

> ⚠️ Web Push chỉ chạy trên **HTTPS** (hoặc localhost). Vì vậy phải **deploy** mới
> dùng được trên điện thoại. Trên iPhone cần iOS 16.4+ và "Thêm vào MH chính".

### Đổi sang VAPID key riêng (khuyến nghị cho production)
```bash
python generate_vapid.py     # in ra VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY
```
Đặt 2 giá trị này vào biến môi trường (xem `.env.example`).

## 🚀 Deploy (Render.com — free)

1. Push code lên GitHub (đã xong).
2. Vào Render → **New + → Blueprint** → chọn repo này (đã có `render.yaml`).
3. Render tự tạo web service + ổ đĩa lưu `state.json`.
4. Sau khi có URL (`https://<app>.onrender.com`), tạo cron sáng:
   - Vào https://cron-job.org (free) → tạo job GET:
     `https://<app>.onrender.com/cron/morning?key=<CRON_SECRET>`
   - Chạy mỗi ngày lúc 08:00. (Lấy `CRON_SECRET` trong Render → Environment.)

> Render free ngủ sau khi không dùng → dùng cron ngoài (cron-job.org) để đánh thức
> và gửi thông báo sáng. Host always-on (VPS) thì đặt `ENABLE_SCHEDULER=1` là đủ.

Các host khác (Railway/Fly/Heroku) dùng `Procfile` sẵn có.

## Cấu trúc

```
couple_questions/
├── app.py              # Flask: câu hỏi, daily/answer/reveal/history, web push, cron
├── templates/
│   └── index.html      # Giao diện mobile (today + history + notif opt-in)
├── static/
│   ├── sw.js           # Service worker (push)
│   ├── manifest.json   # PWA manifest
│   └── icon-192/512.png
├── generate_vapid.py   # Tạo VAPID key riêng
├── render.yaml         # Blueprint deploy Render
├── Procfile            # gunicorn (Railway/Heroku/Fly)
├── runtime.txt         # Python 3.11
├── .env.example        # Mẫu biến môi trường
├── requirements.txt
└── README.md
```

## API

| Endpoint | Method | Mô tả |
|---|---|---|
| `/api/today` | GET | Câu hỏi hôm nay + trạng thái trả lời |
| `/api/answer` | POST | Gửi câu trả lời `{who, text}` |
| `/api/reveal` | POST | Mở câu trả lời (cần cả hai đã trả lời) |
| `/api/partners` | GET/POST | Tên hai người |
| `/api/history` | GET | Lịch sử các ngày đã reveal |
| `/api/vapid-public` | GET | Public key cho push |
| `/api/subscribe` | POST | Lưu subscription `{who, subscription}` |
| `/cron/morning` | GET | Gửi thông báo sáng (cần `?key=CRON_SECRET`) |

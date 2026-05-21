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

## Cấu trúc

```
couple_questions/
├── app.py              # Flask server, câu hỏi, logic daily/answer/reveal/history
├── templates/
│   └── index.html      # Giao diện mobile (today + history tabs)
├── state.json          # Câu hỏi mỗi ngày + câu trả lời (tự tạo, KHÔNG commit)
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

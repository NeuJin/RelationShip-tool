# ❤️ Hỏi Nhau Đi

Web app dành cho các cặp đôi — random câu hỏi để khám phá nhau sâu hơn.  
Giao diện mobile-friendly, đánh dấu câu đã hỏi để không bị lặp lại.

---

## Tính năng

- 🎲 **Random câu hỏi** từ 80 câu thuộc 10 chủ đề
- ✅ **Đánh dấu "Hỏi rồi"** — câu đó không xuất hiện lại
- ⏭️ **Bỏ qua** — chuyển câu khác mà không đánh dấu
- 📊 **Progress bar** — theo dõi tiến trình
- 🔄 **Reset** để bắt đầu lại từ đầu
- 📱 **Mobile-first** — dùng thoải mái trên điện thoại

## 10 chủ đề câu hỏi

| | Chủ đề |
|---|---|
| 💭 | Ký ức & Quá khứ |
| ✨ | Mơ ước & Tương lai |
| ❤️ | Tình yêu & Mối quan hệ |
| 🌟 | Giá trị & Niềm tin |
| 🌿 | Sợ hãi & Dễ tổn thương |
| 🏡 | Gia đình & Bạn bè |
| ☀️ | Cuộc sống hàng ngày |
| 🚀 | Tăng trưởng bản thân |
| 🎨 | Vui & Sáng tạo |
| 🦄 | Kỳ quặc & Thú vị |

---

## Cài đặt & Chạy

```bash
pip install -r requirements.txt
python app.py
```

Mở trình duyệt tại `http://localhost:5000`

**Dùng trên điện thoại (cùng WiFi):**  
Khi khởi động, app sẽ in ra địa chỉ IP — mở địa chỉ đó trên điện thoại là được.

---

## Cấu trúc

```
couple_questions/
├── app.py              # Flask server + danh sách câu hỏi
├── templates/
│   └── index.html      # Giao diện mobile
├── state.json          # Tiến trình (tự tạo, không commit)
├── requirements.txt
└── README.md
```

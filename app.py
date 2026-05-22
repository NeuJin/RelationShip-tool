from flask import Flask, render_template, jsonify, request, send_from_directory, Response
import json, os, random

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DATA_DIR lets a host mount a persistent disk (e.g. Render /var/data).
DATA_DIR = os.environ.get('DATA_DIR', BASE_DIR)
os.makedirs(DATA_DIR, exist_ok=True)
STATE_FILE = os.path.join(DATA_DIR, 'state.json')

# ── Web Push (VAPID) config ──────────────────────────────────────
# Override these via environment variables in production.
# Dev fallback keys included so it works out of the box locally.
VAPID_PUBLIC_KEY = os.environ.get(
    'VAPID_PUBLIC_KEY',
    'BMRcZQ1SWv0NEh1-KYPDICERS2Dsfm4VpDRQfE5LMKQzOjreZ7LMeTH_a5hTxkP6xEPMAbDqK-aviln8w1NY5dI')
VAPID_PRIVATE_KEY = os.environ.get(
    'VAPID_PRIVATE_KEY',
    '1raCjeYLOLiQzZ0eCMifHOHGUs0gMv-0IzoIcnLbn-A')
VAPID_SUBJECT = os.environ.get('VAPID_SUBJECT', 'mailto:hello@forourrelationship.app')
# Secret guarding the external cron endpoint (set in production).
CRON_SECRET = os.environ.get('CRON_SECRET', 'dev-cron-secret')

try:
    from pywebpush import webpush, WebPushException
    _PUSH_OK = True
except Exception:
    _PUSH_OK = False

QUESTIONS = [
    # === Ký ức & Quá khứ ===
    {"id": 1,  "category": "Ký ức & Quá khứ",         "emoji": "💭",
     "text": "Kỷ niệm tuổi thơ nào ảnh hưởng nhiều nhất đến con người bạn ngày hôm nay?"},
    {"id": 2,  "category": "Ký ức & Quá khứ",         "emoji": "💭",
     "text": "Điều gì từ quá khứ bạn vẫn còn tiếc nuối cho đến bây giờ?"},
    {"id": 3,  "category": "Ký ức & Quá khứ",         "emoji": "💭",
     "text": "Người thầy, cô hoặc mentor nào ảnh hưởng lớn nhất đến bạn và tại sao?"},
    {"id": 4,  "category": "Ký ức & Quá khứ",         "emoji": "💭",
     "text": "Kỷ niệm đẹp nhất trong tuổi thơ của bạn là gì?"},
    {"id": 5,  "category": "Ký ức & Quá khứ",         "emoji": "💭",
     "text": "Có điều gì bạn làm hồi nhỏ mà bây giờ nhìn lại thấy rất buồn cười không?"},
    {"id": 58, "category": "Ký ức & Quá khứ",         "emoji": "💭",
     "text": "Bài hát nào gợi lên ký ức mạnh nhất với bạn?"},

    # === Mơ ước & Tương lai ===
    {"id": 6,  "category": "Mơ ước & Tương lai",      "emoji": "✨",
     "text": "Nếu không bị giới hạn bởi tiền bạc hay thời gian, bạn muốn làm gì trong cuộc đời?"},
    {"id": 7,  "category": "Mơ ước & Tương lai",      "emoji": "✨",
     "text": "10 năm nữa bạn muốn cuộc sống của mình trông như thế nào?"},
    {"id": 8,  "category": "Mơ ước & Tương lai",      "emoji": "✨",
     "text": "Có điều gì bạn muốn thử ít nhất một lần trong đời không?"},
    {"id": 9,  "category": "Mơ ước & Tương lai",      "emoji": "✨",
     "text": "Nếu có thể thay đổi một điều về tương lai, bạn sẽ chọn điều gì?"},
    {"id": 10, "category": "Mơ ước & Tương lai",      "emoji": "✨",
     "text": "Bạn mơ về ngôi nhà tổ ấm của mình như thế nào?"},
    {"id": 79, "category": "Mơ ước & Tương lai",      "emoji": "✨",
     "text": "Điều gì về tương lai chung của chúng ta khiến bạn hào hứng nhất?"},

    # === Tình yêu & Mối quan hệ ===
    {"id": 11, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Lần đầu tiên bạn biết rằng mình yêu tôi là khi nào?"},
    {"id": 12, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Điều gì trong mối quan hệ của chúng ta bạn trân trọng nhất?"},
    {"id": 13, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Kỷ niệm nào về chúng ta làm bạn mỉm cười mỗi khi nhớ lại?"},
    {"id": 14, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Điều gì làm bạn cảm thấy được yêu thương và trân trọng nhất?"},
    {"id": 15, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Có điều gì bạn muốn nói với tôi nhưng chưa tìm được cơ hội không?"},
    {"id": 16, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Điều gì trong tính cách của tôi mà bạn ngưỡng mộ nhất?"},
    {"id": 17, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Nếu viết một lá thư cho tôi 10 năm sau, bạn sẽ viết gì?"},
    {"id": 18, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Điều gì trong mối quan hệ của chúng ta bạn nghĩ hai đứa mình nên cải thiện?"},
    {"id": 19, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Hành động nhỏ nào của tôi khiến bạn cảm thấy hạnh phúc nhất?"},
    {"id": 20, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Nếu chúng ta có thể du lịch đến bất cứ đâu cùng nhau, bạn muốn đi đâu nhất?"},
    {"id": 62, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Điều gì bạn muốn tôi hiểu về bạn hơn?"},
    {"id": 66, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Bạn cảm thấy kết nối với tôi nhất trong những khoảnh khắc nào?"},
    {"id": 67, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Có điều gì bạn muốn chúng ta cùng nhau thực hiện trước khi năm kết thúc không?"},
    {"id": 69, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Nếu chúng ta có thể 'quay ngược thời gian' để sống lại một khoảnh khắc, bạn sẽ chọn khoảnh khắc nào?"},
    {"id": 71, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Bạn thích nhận lời xin lỗi như thế nào — bằng lời nói, hành động hay cử chỉ?"},
    {"id": 72, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Điều gì trong tôi đã thay đổi theo thời gian và bạn trân trọng sự thay đổi đó?"},
    {"id": 75, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Cuộc trò chuyện nào giữa chúng ta bạn nhớ mãi không quên?"},
    {"id": 76, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Bạn nghĩ điểm mạnh lớn nhất của mối quan hệ chúng ta là gì?"},
    {"id": 77, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Điều gì khiến bạn cảm thấy rằng chúng ta thực sự 'hiểu' nhau?"},
    {"id": 80, "category": "Tình yêu & Mối quan hệ",  "emoji": "❤️",
     "text": "Câu hỏi nào bạn luôn muốn hỏi tôi nhưng chưa dám hỏi?"},

    # === Giá trị & Niềm tin ===
    {"id": 21, "category": "Giá trị & Niềm tin",      "emoji": "🌟",
     "text": "Điều gì là quan trọng nhất với bạn trong cuộc sống?"},
    {"id": 22, "category": "Giá trị & Niềm tin",      "emoji": "🌟",
     "text": "Giá trị nào bạn không bao giờ muốn từ bỏ, dù trong hoàn cảnh nào?"},
    {"id": 23, "category": "Giá trị & Niềm tin",      "emoji": "🌟",
     "text": "Bạn tin vào điều gì một cách mạnh mẽ mà nhiều người có thể không đồng ý?"},
    {"id": 24, "category": "Giá trị & Niềm tin",      "emoji": "🌟",
     "text": "Thành công đối với bạn có nghĩa là gì?"},
    {"id": 25, "category": "Giá trị & Niềm tin",      "emoji": "🌟",
     "text": "Điều gì tạo ra ý nghĩa và mục đích trong cuộc sống của bạn?"},
    {"id": 64, "category": "Giá trị & Niềm tin",      "emoji": "🌟",
     "text": "Bạn xác định 'nhà' là gì — là nơi chốn hay là người?"},
    {"id": 68, "category": "Giá trị & Niềm tin",      "emoji": "🌟",
     "text": "Điều gì khiến bạn cảm thấy cuộc sống thực sự đáng sống?"},
    {"id": 74, "category": "Giá trị & Niềm tin",      "emoji": "🌟",
     "text": "Điều gì bạn muốn con cái chúng ta (nếu có) học được từ cách chúng ta yêu nhau?"},

    # === Sợ hãi & Dễ tổn thương ===
    {"id": 26, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿",
     "text": "Điều gì khiến bạn sợ hãi nhất trong cuộc sống?"},
    {"id": 27, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿",
     "text": "Khoảnh khắc nào trong cuộc đời bạn cảm thấy dễ tổn thương nhất?"},
    {"id": 28, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿",
     "text": "Điều gì bạn thường tránh né vì sợ thất bại?"},
    {"id": 29, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿",
     "text": "Có điều gì bạn cảm thấy xấu hổ về bản thân không? Bạn đã vượt qua nó như thế nào?"},
    {"id": 30, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿",
     "text": "Điều gì giữ bạn thức đêm lo lắng nhiều nhất?"},

    # === Gia đình & Bạn bè ===
    {"id": 31, "category": "Gia đình & Bạn bè",       "emoji": "🏡",
     "text": "Thành viên gia đình nào ảnh hưởng lớn nhất đến con người bạn?"},
    {"id": 32, "category": "Gia đình & Bạn bè",       "emoji": "🏡",
     "text": "Điều gì bạn học được từ cha mẹ mà bạn muốn truyền lại cho thế hệ tiếp theo?"},
    {"id": 33, "category": "Gia đình & Bạn bè",       "emoji": "🏡",
     "text": "Điều gì bạn muốn thay đổi về cách bạn được nuôi dưỡng?"},
    {"id": 34, "category": "Gia đình & Bạn bè",       "emoji": "🏡",
     "text": "Người bạn thân nhất của bạn biết gì về bạn mà tôi chưa biết?"},
    {"id": 35, "category": "Gia đình & Bạn bè",       "emoji": "🏡",
     "text": "Kỷ niệm gia đình nào bạn trân trọng nhất?"},

    # === Cuộc sống hàng ngày ===
    {"id": 36, "category": "Cuộc sống hàng ngày",     "emoji": "☀️",
     "text": "Thói quen buổi sáng lý tưởng của bạn trông như thế nào?"},
    {"id": 37, "category": "Cuộc sống hàng ngày",     "emoji": "☀️",
     "text": "Bạn cần gì để cảm thấy thực sự thư giãn và hồi phục năng lượng?"},
    {"id": 38, "category": "Cuộc sống hàng ngày",     "emoji": "☀️",
     "text": "Điều nhỏ nào trong ngày thường làm cho bạn hạnh phúc?"},
    {"id": 39, "category": "Cuộc sống hàng ngày",     "emoji": "☀️",
     "text": "Khi bạn stress, bạn cần gì từ tôi nhất?"},
    {"id": 40, "category": "Cuộc sống hàng ngày",     "emoji": "☀️",
     "text": "Bữa ăn hoàn hảo theo bạn là gì?"},
    {"id": 65, "category": "Cuộc sống hàng ngày",     "emoji": "☀️",
     "text": "Điều gì tạo nên một ngày hoàn hảo với bạn?"},

    # === Tăng trưởng bản thân ===
    {"id": 41, "category": "Tăng trưởng bản thân",    "emoji": "🚀",
     "text": "Bạn đã thay đổi như thế nào kể từ khi chúng ta ở bên nhau?"},
    {"id": 42, "category": "Tăng trưởng bản thân",    "emoji": "🚀",
     "text": "Điều gì bạn muốn học hoặc phát triển trong năm tới?"},
    {"id": 43, "category": "Tăng trưởng bản thân",    "emoji": "🚀",
     "text": "Thất bại lớn nhất của bạn đã dạy bạn điều gì?"},
    {"id": 44, "category": "Tăng trưởng bản thân",    "emoji": "🚀",
     "text": "Phiên bản tốt nhất của bản thân trông như thế nào với bạn?"},
    {"id": 45, "category": "Tăng trưởng bản thân",    "emoji": "🚀",
     "text": "Điều gì bạn tự hào nhất về sự phát triển của mình?"},
    {"id": 57, "category": "Tăng trưởng bản thân",    "emoji": "🚀",
     "text": "Nếu bạn có thể nói chuyện với bản thân 10 tuổi, bạn sẽ nói gì?"},
    {"id": 60, "category": "Tăng trưởng bản thân",    "emoji": "🚀",
     "text": "Điều gì bạn cần học cách 'buông bỏ' hơn trong cuộc sống?"},
    {"id": 61, "category": "Tăng trưởng bản thân",    "emoji": "🚀",
     "text": "Khoảnh khắc nào trong cuộc đời bạn cảm thấy tự hào nhất?"},
    {"id": 70, "category": "Tăng trưởng bản thân",    "emoji": "🚀",
     "text": "Bạn học được điều gì về bản thân mình qua những mối quan hệ trước đây?"},

    # === Vui & Sáng tạo ===
    {"id": 46, "category": "Vui & Sáng tạo",          "emoji": "🎨",
     "text": "Nếu bạn có thể có siêu năng lực nào, bạn sẽ chọn gì và dùng nó như thế nào?"},
    {"id": 47, "category": "Vui & Sáng tạo",          "emoji": "🎨",
     "text": "Nếu cuộc sống của bạn là một bộ phim, nó thuộc thể loại gì và tên phim là gì?"},
    {"id": 48, "category": "Vui & Sáng tạo",          "emoji": "🎨",
     "text": "Bạn sẽ làm gì nếu biết mình không thể thất bại?"},
    {"id": 49, "category": "Vui & Sáng tạo",          "emoji": "🎨",
     "text": "Nếu phải chọn sống ở bất kỳ thời đại lịch sử nào khác, bạn sẽ chọn thời nào?"},
    {"id": 50, "category": "Vui & Sáng tạo",          "emoji": "🎨",
     "text": "Trò chơi hoặc hoạt động nào từ thời thơ ấu bạn muốn làm lại ngay bây giờ?"},
    {"id": 56, "category": "Vui & Sáng tạo",          "emoji": "🎨",
     "text": "Điều gì khiến bạn bật cười ngay cả khi đang buồn?"},
    {"id": 59, "category": "Vui & Sáng tạo",          "emoji": "🎨",
     "text": "Nếu bạn viết một cuốn sách, nó sẽ về chủ đề gì?"},
    {"id": 63, "category": "Vui & Sáng tạo",          "emoji": "🎨",
     "text": "Nếu chúng ta mở một quán cà phê cùng nhau, nó sẽ có phong cách như thế nào?"},
    {"id": 73, "category": "Vui & Sáng tạo",          "emoji": "🎨",
     "text": "Nếu phải mô tả tình yêu của chúng ta bằng một màu sắc, bạn sẽ chọn màu gì và tại sao?"},
    {"id": 78, "category": "Vui & Sáng tạo",          "emoji": "🎨",
     "text": "Nếu bạn có thể tặng tôi bất kỳ trải nghiệm nào không giới hạn tiền, bạn sẽ tặng gì?"},

    # === Kỳ quặc & Thú vị ===
    {"id": 51, "category": "Kỳ quặc & Thú vị",        "emoji": "🦄",
     "text": "Bạn có thói quen kỳ lạ nào mà ít người biết không?"},
    {"id": 52, "category": "Kỳ quặc & Thú vị",        "emoji": "🦄",
     "text": "Điều ngớ ngẩn nhất bạn từng làm vì tình yêu hoặc vì ai đó là gì?"},
    {"id": 53, "category": "Kỳ quặc & Thú vị",        "emoji": "🦄",
     "text": "Nếu bạn là một loài động vật, bạn sẽ là con gì và tại sao?"},
    {"id": 54, "category": "Kỳ quặc & Thú vị",        "emoji": "🦄",
     "text": "Món ăn nào bạn bí mật thích dù biết nó bị nhiều người chê?"},
    {"id": 55, "category": "Kỳ quặc & Thú vị",        "emoji": "🦄",
     "text": "Bạn có niềm tin hoặc mê tín nào thú vị không?"},

    # ========= BỘ CÂU HỎI MỞ RỘNG (tham khảo Gottman, 36 Questions, The And, WNRS...) =========
    # --- Tình yêu & Mối quan hệ ---
    {"id": 81, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️",
     "text": "Lần gần đây nhất bạn thấy mình thực sự được tôi lắng nghe là khi nào?"},
    {"id": 82, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️",
     "text": "Có thói quen nhỏ nào của tôi mà bạn thầm yêu thích không?"},
    {"id": 83, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️",
     "text": "Bạn muốn chúng ta thể hiện tình cảm với nhau nhiều hơn theo cách nào?"},
    {"id": 84, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️",
     "text": "Điều gì khiến bạn cảm thấy an toàn nhất khi ở bên tôi?"},
    {"id": 85, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️",
     "text": "Khi chúng ta giận nhau, điều gì giúp bạn nguôi giận nhanh nhất?"},
    {"id": 86, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️",
     "text": "Bạn nghĩ chúng ta đã cùng nhau vượt qua thử thách lớn nhất nào?"},
    {"id": 87, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️",
     "text": "Có điều gì bạn từng hiểu lầm về tôi rồi sau này mới nhận ra không?"},
    {"id": 88, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️",
     "text": "Bạn muốn được tôi ủng hộ thế nào khi theo đuổi điều mình mơ ước?"},
    {"id": 89, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️",
     "text": "Ngôn ngữ tình yêu nào khiến bạn cảm nhận được yêu nhất: lời nói, hành động, quà, thời gian bên nhau hay cử chỉ âu yếm?"},
    {"id": 90, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️",
     "text": "Điều gì ở giai đoạn đầu yêu nhau mà bạn muốn chúng ta giữ lại mãi?"},
    {"id": 128, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️",
     "text": "Điều gì khiến bạn cảm thấy được tôi ưu tiên trong cuộc sống?"},
    {"id": 129, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️",
     "text": "Khi xa nhau, bạn nhớ điều gì ở tôi nhất?"},
    {"id": 130, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️",
     "text": "Có lời khen nào của tôi mà bạn nhớ mãi không?"},
    {"id": 131, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️",
     "text": "Bạn muốn chúng ta giải quyết bất đồng theo 'nguyên tắc' nào?"},
    {"id": 150, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️",
     "text": "Nếu chỉ được nói một điều để tôi luôn ghi nhớ về tình yêu của bạn, đó sẽ là gì?"},

    # --- Sợ hãi & Dễ tổn thương ---
    {"id": 91, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿",
     "text": "Bạn sợ nhất điều gì có thể xảy ra với mối quan hệ của chúng ta?"},
    {"id": 92, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿",
     "text": "Khi nào bạn thấy khó mở lòng với tôi nhất?"},
    {"id": 93, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿",
     "text": "Có nỗi buồn nào bạn thường giấu đi thay vì chia sẻ với tôi không?"},
    {"id": 94, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿",
     "text": "Điều gì khiến bạn cảm thấy mình 'chưa đủ tốt', và tôi có thể giúp gì?"},
    {"id": 132, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿",
     "text": "Có điều gì bạn cần ở tôi nhưng còn ngại nói ra không?"},
    {"id": 133, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿",
     "text": "Khi bạn im lặng, thường thì lúc đó bạn đang cần điều gì?"},
    {"id": 149, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿",
     "text": "Gần đây có điều gì làm bạn áp lực mà tôi chưa biết không?"},

    # --- Mơ ước & Tương lai ---
    {"id": 95, "category": "Mơ ước & Tương lai", "emoji": "✨",
     "text": "Bạn hình dung một ngày bình thường của chúng ta sau 5 năm nữa ra sao?"},
    {"id": 96, "category": "Mơ ước & Tương lai", "emoji": "✨",
     "text": "Có truyền thống nhỏ nào bạn muốn chúng ta cùng tạo ra không?"},
    {"id": 97, "category": "Mơ ước & Tương lai", "emoji": "✨",
     "text": "Nếu cùng nhau thực hiện một dự án lớn, bạn muốn đó là gì?"},
    {"id": 98, "category": "Mơ ước & Tương lai", "emoji": "✨",
     "text": "Bạn muốn chúng ta cùng học một điều gì mới với nhau?"},
    {"id": 99, "category": "Mơ ước & Tương lai", "emoji": "✨",
     "text": "Tuổi già lý tưởng bên nhau trong mắt bạn trông như thế nào?"},
    {"id": 134, "category": "Mơ ước & Tương lai", "emoji": "✨",
     "text": "Bạn muốn chúng ta để lại cho nhau điều gì như một 'di sản tình yêu'?"},
    {"id": 135, "category": "Mơ ước & Tương lai", "emoji": "✨",
     "text": "Nếu sau này có con, bạn muốn dạy con điều quan trọng nhất là gì?"},

    # --- Giá trị & Niềm tin ---
    {"id": 100, "category": "Giá trị & Niềm tin", "emoji": "🌟",
     "text": "Tiền bạc nên đóng vai trò gì trong cuộc sống chung của chúng ta?"},
    {"id": 101, "category": "Giá trị & Niềm tin", "emoji": "🌟",
     "text": "Với bạn, 'chung thủy' còn có nghĩa gì ngoài việc không phản bội?"},
    {"id": 102, "category": "Giá trị & Niềm tin", "emoji": "🌟",
     "text": "Điều gì bạn tuyệt đối không thể thỏa hiệp trong một mối quan hệ?"},
    {"id": 103, "category": "Giá trị & Niềm tin", "emoji": "🌟",
     "text": "Bạn định nghĩa một gia đình hạnh phúc như thế nào?"},
    {"id": 136, "category": "Giá trị & Niềm tin", "emoji": "🌟",
     "text": "Tha thứ với bạn là dễ hay khó? Điều gì giúp bạn tha thứ?"},
    {"id": 137, "category": "Giá trị & Niềm tin", "emoji": "🌟",
     "text": "Điều gì khiến bạn cảm thấy được tôn trọng?"},

    # --- Ký ức & Quá khứ ---
    {"id": 104, "category": "Ký ức & Quá khứ", "emoji": "💭",
     "text": "Lần đầu gặp tôi, ấn tượng thật sự của bạn là gì?"},
    {"id": 105, "category": "Ký ức & Quá khứ", "emoji": "💭",
     "text": "Khoảnh khắc nào khiến bạn quyết định muốn ở bên tôi lâu dài?"},
    {"id": 106, "category": "Ký ức & Quá khứ", "emoji": "💭",
     "text": "Có kỷ niệm chung nào bạn ước mình đã trân trọng hơn lúc đó không?"},
    {"id": 107, "category": "Ký ức & Quá khứ", "emoji": "💭",
     "text": "Câu chuyện nào về chúng ta bạn thích kể cho người khác nghe nhất?"},
    {"id": 138, "category": "Ký ức & Quá khứ", "emoji": "💭",
     "text": "Khoảnh khắc nào bạn thấy tôi đáng yêu nhất?"},
    {"id": 139, "category": "Ký ức & Quá khứ", "emoji": "💭",
     "text": "Lần nào bạn thấy tự hào về tôi nhất?"},

    # --- Gia đình & Bạn bè ---
    {"id": 108, "category": "Gia đình & Bạn bè", "emoji": "🏡",
     "text": "Bạn muốn mối quan hệ của chúng ta với gia đình hai bên như thế nào?"},
    {"id": 109, "category": "Gia đình & Bạn bè", "emoji": "🏡",
     "text": "Có điều gì từ gia đình bạn mà bạn muốn — hoặc không muốn — lặp lại trong nhà mình?"},
    {"id": 110, "category": "Gia đình & Bạn bè", "emoji": "🏡",
     "text": "Người bạn nào của tôi mà bạn quý nhất, vì sao?"},
    {"id": 148, "category": "Gia đình & Bạn bè", "emoji": "🏡",
     "text": "Bạn muốn những ngày lễ, Tết của chúng ta diễn ra như thế nào?"},

    # --- Cuộc sống hàng ngày ---
    {"id": 111, "category": "Cuộc sống hàng ngày", "emoji": "☀️",
     "text": "Việc nhà nào bạn thực sự ghét, và việc nào bạn không phiền làm?"},
    {"id": 112, "category": "Cuộc sống hàng ngày", "emoji": "☀️",
     "text": "Buổi tối hoàn hảo của hai ta sau một ngày dài là gì?"},
    {"id": 113, "category": "Cuộc sống hàng ngày", "emoji": "☀️",
     "text": "Bạn thích được đánh thức vào buổi sáng theo cách nào?"},
    {"id": 114, "category": "Cuộc sống hàng ngày", "emoji": "☀️",
     "text": "Điều nhỏ nào tôi làm khiến một ngày của bạn dễ chịu hơn?"},
    {"id": 140, "category": "Cuộc sống hàng ngày", "emoji": "☀️",
     "text": "Cuối tuần lý tưởng của hai ta là chill ở nhà hay đi chơi?"},
    {"id": 141, "category": "Cuộc sống hàng ngày", "emoji": "☀️",
     "text": "Bạn muốn chúng ta có 'nghi thức' nhỏ nào mỗi ngày — ôm, nhắn tin, hay gọi điện?"},

    # --- Tăng trưởng bản thân ---
    {"id": 115, "category": "Tăng trưởng bản thân", "emoji": "🚀",
     "text": "Bạn đang cố gắng trở thành phiên bản nào của chính mình?"},
    {"id": 116, "category": "Tăng trưởng bản thân", "emoji": "🚀",
     "text": "Tôi có thể làm gì để giúp bạn phát triển mà không tạo áp lực?"},
    {"id": 117, "category": "Tăng trưởng bản thân", "emoji": "🚀",
     "text": "Thói quen nào bạn muốn bỏ, và muốn tôi đồng hành ra sao?"},
    {"id": 118, "category": "Tăng trưởng bản thân", "emoji": "🚀",
     "text": "Bạn tự hào nhất về điều gì mình đã làm trong năm qua?"},
    {"id": 142, "category": "Tăng trưởng bản thân", "emoji": "🚀",
     "text": "Bạn học được điều quan trọng nhất gì từ chính mối quan hệ này?"},
    {"id": 143, "category": "Tăng trưởng bản thân", "emoji": "🚀",
     "text": "Có điều gì bạn muốn cả hai cùng cố gắng nhiều hơn không?"},

    # --- Vui & Sáng tạo ---
    {"id": 119, "category": "Vui & Sáng tạo", "emoji": "🎨",
     "text": "Nếu hai ta có một bài hát 'của riêng mình', bạn muốn đó là bài nào?"},
    {"id": 120, "category": "Vui & Sáng tạo", "emoji": "🎨",
     "text": "Chuyến đi trong mơ của chúng ta sẽ diễn ra ở đâu và làm gì?"},
    {"id": 121, "category": "Vui & Sáng tạo", "emoji": "🎨",
     "text": "Nếu có một buổi hẹn hò bất ngờ, bạn muốn tôi đưa đi đâu?"},
    {"id": 122, "category": "Vui & Sáng tạo", "emoji": "🎨",
     "text": "Biệt danh nào bạn muốn tôi gọi bạn nhất?"},
    {"id": 123, "category": "Vui & Sáng tạo", "emoji": "🎨",
     "text": "Nếu cuộc tình của chúng ta là một cuốn phim, cảnh mở đầu sẽ thế nào?"},
    {"id": 144, "category": "Vui & Sáng tạo", "emoji": "🎨",
     "text": "Nếu được tặng nhau một ngày 'làm bất cứ điều gì', bạn chọn làm gì cùng tôi?"},
    {"id": 145, "category": "Vui & Sáng tạo", "emoji": "🎨",
     "text": "Ba thứ luôn khiến bạn nghĩ đến tôi là gì?"},

    # --- Kỳ quặc & Thú vị ---
    {"id": 124, "category": "Kỳ quặc & Thú vị", "emoji": "🦄",
     "text": "Thói quen nào của tôi lúc đầu thấy lạ nhưng giờ bạn thấy đáng yêu?"},
    {"id": 125, "category": "Kỳ quặc & Thú vị", "emoji": "🦄",
     "text": "Món ăn 'tội lỗi' nào mà hai ta nhất định nên cùng thử?"},
    {"id": 126, "category": "Kỳ quặc & Thú vị", "emoji": "🦄",
     "text": "Nếu bị kẹt trên đảo hoang cùng nhau, bạn lo nhất điều gì ở tôi?"},
    {"id": 127, "category": "Kỳ quặc & Thú vị", "emoji": "🦄",
     "text": "Trò 'nhây' nào của chúng ta mà chỉ hai đứa mới hiểu?"},
    {"id": 146, "category": "Kỳ quặc & Thú vị", "emoji": "🦄",
     "text": "Nếu hai ta là một cặp nhân vật trong phim hay truyện, đó sẽ là ai?"},
    {"id": 147, "category": "Kỳ quặc & Thú vị", "emoji": "🦄",
     "text": "Điều 'dở hơi' nào ở tôi mà bạn sẽ nhớ nếu một ngày nó biến mất?"},

    # ============ BỘ MỞ RỘNG LỚN (ID 151–500) ============
    # --- Tình yêu & Mối quan hệ (151–225) ---
    {"id": 151, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Khoảnh khắc nào trong tuần này khiến bạn thấy biết ơn vì có tôi?"},
    {"id": 152, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Tôi làm điều gì khiến bạn cảm thấy được trân trọng nhất?"},
    {"id": 153, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Có cử chỉ yêu thương nào của tôi mà bạn mong nhận được thường xuyên hơn?"},
    {"id": 154, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn thích được tôi ôm vào lúc nào nhất trong ngày?"},
    {"id": 155, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Điều gì ở nụ cười của tôi khiến bạn chú ý?"},
    {"id": 156, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Khi bạn buồn, bạn muốn tôi ở bên im lặng hay trò chuyện?"},
    {"id": 157, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Lần gần nhất tôi khiến bạn bất ngờ là vì điều gì?"},
    {"id": 158, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn nghĩ tình yêu của chúng ta đã 'lớn lên' như thế nào theo thời gian?"},
    {"id": 159, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Có câu nói nào của tôi mà bạn luôn muốn nghe lại?"},
    {"id": 160, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn cảm thấy gần gũi với tôi nhất khi chúng ta làm gì cùng nhau?"},
    {"id": 161, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Điều gì khiến bạn tin rằng tôi thực sự hiểu bạn?"},
    {"id": 162, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn muốn chúng ta dành buổi tối bên nhau khác đi như thế nào?"},
    {"id": 163, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Có thói quen chung nào của hai ta mà bạn rất trân trọng?"},
    {"id": 164, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Khi tôi mệt mỏi, bạn nhận ra qua dấu hiệu nào?"},
    {"id": 165, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn muốn được tôi khen về điều gì nhiều hơn?"},
    {"id": 166, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Điều nhỏ nào tôi từng làm mà bạn vẫn nhớ đến giờ?"},
    {"id": 167, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn thấy chúng ta hợp nhau nhất ở điểm nào?"},
    {"id": 168, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Khác biệt nào giữa hai ta mà bạn thấy lại bổ sung cho nhau?"},
    {"id": 169, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn muốn chúng ta cùng nhau 'tắt điện thoại' để làm gì?"},
    {"id": 170, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Có điều gì bạn chưa từng cảm ơn tôi nhưng luôn ghi nhớ?"},
    {"id": 171, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn muốn tôi chủ động hơn trong việc gì?"},
    {"id": 172, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Điều gì khiến bạn cảm thấy chúng ta là một 'đội'?"},
    {"id": 173, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn nhớ nhất điều gì về lần hẹn hò đầu tiên của chúng ta?"},
    {"id": 174, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Nếu phải nhắc tôi một điều mỗi sáng, bạn muốn nhắc gì?"},
    {"id": 175, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn muốn chúng ta nói lời yêu theo cách nào khác ngoài lời nói?"},
    {"id": 176, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Có giai đoạn nào của chúng ta bạn muốn sống lại không?"},
    {"id": 177, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn cảm thấy được yêu khi tôi nhớ những điều nhỏ nào về bạn?"},
    {"id": 178, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Điều gì ở cách tôi quan tâm bạn mà bạn thích nhất?"},
    {"id": 179, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn muốn chúng ta cùng tạo thói quen mới nào cho tình cảm?"},
    {"id": 180, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Khi xa nhau cả ngày, điều đầu tiên bạn muốn kể cho tôi là gì?"},
    {"id": 181, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn nghĩ điều gì giữ cho tình yêu lâu dài không nhàm chán?"},
    {"id": 182, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Có 'ngôn ngữ riêng' nào giữa hai ta mà bạn yêu thích?"},
    {"id": 183, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn muốn tôi lắng nghe bạn nhiều hơn về chủ đề gì?"},
    {"id": 184, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Điều gì khiến bạn yên tâm rằng chúng ta sẽ ổn dù khó khăn?"},
    {"id": 185, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn thích bản thân mình hơn ở điểm nào khi ở bên tôi?"},
    {"id": 186, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Có điều gì bạn muốn chúng ta tha thứ cho nhau và bỏ lại phía sau?"},
    {"id": 187, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn muốn kỷ niệm những ngày đặc biệt của chúng ta như thế nào?"},
    {"id": 188, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Tôi có thói quen nào khiến bạn thấy được yêu mà tôi không để ý?"},
    {"id": 189, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn muốn chúng ta dành nhiều thời gian hơn cho điều gì?"},
    {"id": 190, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Điều gì ở tôi khiến bạn thấy tự hào khi giới thiệu với người khác?"},
    {"id": 191, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn muốn tôi thể hiện sự ủng hộ khi bạn thất bại như thế nào?"},
    {"id": 192, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Có khoảnh khắc đời thường nào bên tôi khiến bạn thấy hạnh phúc bất ngờ?"},
    {"id": 193, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn nghĩ chúng ta nên 'làm mới' tình cảm bằng cách nào?"},
    {"id": 194, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Điều gì khiến bạn cảm thấy được tôi ưu tiên hơn mọi thứ khác?"},
    {"id": 195, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn muốn nghe tôi xin lỗi theo cách nào để thực sự thấy được?"},
    {"id": 196, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Có nỗi sợ nào về tình yêu mà bạn muốn tôi giúp xua tan?"},
    {"id": 197, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn thấy chúng ta giao tiếp tốt nhất vào lúc nào?"},
    {"id": 198, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn học được điều gì về yêu thương từ chính tôi?"},
    {"id": 199, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn muốn chúng ta cùng đặt ra 'luật chơi' nào để yêu nhau bền hơn?"},
    {"id": 200, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Nếu viết một dòng tựa cho chuyện tình của chúng ta, bạn viết gì?"},
    {"id": 201, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn thấy tôi thay đổi tốt lên ở điểm nào kể từ khi yêu nhau?"},
    {"id": 202, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Có điều gì bạn muốn nói 'cảm ơn' với tôi ngay bây giờ?"},
    {"id": 203, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn muốn được an ủi thế nào sau một ngày tồi tệ?"},
    {"id": 204, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Điều gì khiến bạn cảm thấy chúng ta vẫn đang 'tán tỉnh' nhau?"},
    {"id": 205, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn thích nhất khoảnh khắc nào khi thức dậy bên tôi?"},
    {"id": 206, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Có bài hát hay bộ phim nào khiến bạn nghĩ đến chúng ta?"},
    {"id": 207, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn muốn chúng ta cùng vượt qua tính xấu nào của nhau?"},
    {"id": 208, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Điều gì ở tôi làm bạn cảm thấy được che chở?"},
    {"id": 209, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn muốn tôi hỏi thăm bạn về điều gì thường xuyên hơn?"},
    {"id": 210, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Có giấc mơ chung nào bạn muốn nhắc tôi đừng quên?"},
    {"id": 211, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn cảm thấy được tôn trọng nhất khi tôi làm gì?"},
    {"id": 212, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Điều gì khiến bạn muốn ôm tôi thật chặt?"},
    {"id": 213, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn muốn chúng ta chia sẻ với nhau nhiều hơn về điều gì?"},
    {"id": 214, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Có thử thách nào bạn nghĩ sẽ khiến chúng ta mạnh mẽ hơn?"},
    {"id": 215, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn thấy mình may mắn vì điều gì ở tôi?"},
    {"id": 216, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Điều gì ở tôi bạn mong tôi đừng bao giờ thay đổi?"},
    {"id": 217, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn muốn chúng ta cùng nhau 'chậm lại' để tận hưởng điều gì?"},
    {"id": 218, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Có lời hứa nào bạn muốn chúng ta giữ cho nhau?"},
    {"id": 219, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn thấy tình yêu của chúng ta đặc biệt ở chỗ nào?"},
    {"id": 220, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Điều gì khiến một ngày bình thường bên tôi trở nên đáng nhớ?"},
    {"id": 221, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn muốn tôi nhớ điều gì về bạn khi bạn không vui?"},
    {"id": 222, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Có cách nào tôi có thể khiến bạn cười mỗi ngày không?"},
    {"id": 223, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Bạn muốn chúng ta cùng nhau biết ơn điều gì mỗi tối?"},
    {"id": 224, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Điều gì ở mối quan hệ này khiến bạn muốn cố gắng hơn mỗi ngày?"},
    {"id": 225, "category": "Tình yêu & Mối quan hệ", "emoji": "❤️", "text": "Nếu được gửi một tin nhắn cho tôi của một năm trước, bạn nhắn gì?"},

    # --- Sợ hãi & Dễ tổn thương (226–260) ---
    {"id": 226, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Có nỗi sợ nào từ tuổi thơ vẫn ảnh hưởng đến bạn đến giờ?"},
    {"id": 227, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Khi nào bạn cảm thấy cô đơn ngay cả khi ở cạnh người khác?"},
    {"id": 228, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Điều gì khiến bạn khó nói ra câu 'mình cần giúp đỡ'?"},
    {"id": 229, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Bạn sợ người khác nhìn thấy phần nào ở mình nhất?"},
    {"id": 230, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Có ký ức nào khiến bạn tổn thương mà chưa kể với ai?"},
    {"id": 231, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Khi buồn, bạn có xu hướng thu mình hay tìm người chia sẻ?"},
    {"id": 232, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Điều gì khiến bạn cảm thấy bị phán xét?"},
    {"id": 233, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Bạn sợ đánh mất điều gì nhất trong cuộc sống?"},
    {"id": 234, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Có áp lực vô hình nào bạn đang gánh mà ít ai biết?"},
    {"id": 235, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Khi thất bại, bạn thường tự nói với mình điều gì?"},
    {"id": 236, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Điều gì khiến bạn cảm thấy không an toàn?"},
    {"id": 237, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Bạn từng giả vờ ổn trong khi không ổn vì lý do gì?"},
    {"id": 238, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Có lời nói nào trong quá khứ vẫn còn làm bạn đau?"},
    {"id": 239, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Bạn có sợ trở nên giống ai đó không? Vì sao?"},
    {"id": 240, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Điều gì bạn ước người khác hiểu về nỗi buồn của bạn?"},
    {"id": 241, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Khi lo lắng, cơ thể bạn phản ứng thế nào?"},
    {"id": 242, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Bạn khó tha thứ cho bản thân vì điều gì?"},
    {"id": 243, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Có quyết định nào bạn đang sợ phải đối mặt?"},
    {"id": 244, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Bạn cảm thấy dễ tổn thương nhất khi ai đó làm gì?"},
    {"id": 245, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Điều gì khiến bạn muốn bỏ cuộc, và điều gì giữ bạn lại?"},
    {"id": 246, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Bạn sợ bị hiểu lầm về điều gì nhất?"},
    {"id": 247, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Có phần nào trong quá khứ bạn muốn được chữa lành?"},
    {"id": 248, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Bạn thường che giấu cảm xúc bằng cách nào?"},
    {"id": 249, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Điều gì khiến bạn cảm thấy nhỏ bé?"},
    {"id": 250, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Bạn cần nghe điều gì khi đang yếu lòng?"},
    {"id": 251, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Có nỗi sợ nào bạn biết là vô lý nhưng vẫn không bỏ được?"},
    {"id": 252, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Bạn sợ tương lai ở điểm nào nhất?"},
    {"id": 253, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Khi bị tổn thương, bạn mất bao lâu để mở lòng lại?"},
    {"id": 254, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Điều gì khiến bạn cảm thấy bị bỏ rơi?"},
    {"id": 255, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Bạn từng hối hận vì đã không nói ra điều gì?"},
    {"id": 256, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Có giấc mơ nào bạn sợ theo đuổi vì sợ thất bại?"},
    {"id": 257, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Bạn cảm thấy áp lực phải hoàn hảo trong việc gì?"},
    {"id": 258, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Điều gì khiến bạn khó tin tưởng người khác?"},
    {"id": 259, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Bạn sợ mình đang dần trở nên thế nào?"},
    {"id": 260, "category": "Sợ hãi & Dễ tổn thương", "emoji": "🌿", "text": "Có điều gì bạn cần buông bỏ nhưng vẫn đang níu giữ?"},

    # --- Mơ ước & Tương lai (261–300) ---
    {"id": 261, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn muốn 5 năm tới mình sống ở đâu?"},
    {"id": 262, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Có kỹ năng nào bạn mơ được thành thạo?"},
    {"id": 263, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn hình dung 'thành công' của mình ở tuổi 50 thế nào?"},
    {"id": 264, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Nơi nào bạn nhất định phải đặt chân đến một lần trong đời?"},
    {"id": 265, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn muốn nghỉ hưu theo kiểu gì?"},
    {"id": 266, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Có ngành nghề nào bạn ước được thử nếu làm lại từ đầu?"},
    {"id": 267, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn muốn để lại dấu ấn gì cho thế giới?"},
    {"id": 268, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Giấc mơ lớn nhất bạn chưa dám nói với ai là gì?"},
    {"id": 269, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn muốn học ngôn ngữ hay nhạc cụ nào?"},
    {"id": 270, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Nếu có một năm tự do hoàn toàn, bạn sẽ làm gì?"},
    {"id": 271, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn muốn sức khỏe của mình ra sao trong 10 năm tới?"},
    {"id": 272, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Có nơi nào bạn mơ được sống thử một thời gian?"},
    {"id": 273, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn muốn tạo ra điều gì khiến mình tự hào?"},
    {"id": 274, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Mục tiêu nào năm nay bạn quyết tâm đạt được?"},
    {"id": 275, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn muốn xây dựng thói quen tốt nào trong tương lai?"},
    {"id": 276, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Nếu mở một việc kinh doanh, đó sẽ là gì?"},
    {"id": 277, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn muốn dành tiền tiết kiệm cho ước mơ nào?"},
    {"id": 278, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Có trải nghiệm phiêu lưu nào trong danh sách của bạn?"},
    {"id": 279, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn muốn trở thành hình mẫu cho ai?"},
    {"id": 280, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "10 năm nữa bạn muốn người ta nhớ đến mình vì điều gì?"},
    {"id": 281, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn muốn cuối tuần lý tưởng trong tương lai trông thế nào?"},
    {"id": 282, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Có dự án sáng tạo nào bạn muốn hoàn thành?"},
    {"id": 283, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn muốn cải thiện mối quan hệ nào trong tương lai?"},
    {"id": 284, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Nếu viết sách về đời mình, chương tiếp theo tên là gì?"},
    {"id": 285, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn mơ về một ngôi nhà như thế nào?"},
    {"id": 286, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Có thử thách thể chất nào bạn muốn chinh phục?"},
    {"id": 287, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn muốn về già vẫn giữ được điều gì ở bản thân?"},
    {"id": 288, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Giấc mơ nào hồi nhỏ bạn vẫn muốn theo đuổi?"},
    {"id": 289, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn muốn dành nhiều thời gian hơn cho ai trong tương lai?"},
    {"id": 290, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Nếu được sống ở bất kỳ thành phố nào, bạn chọn đâu?"},
    {"id": 291, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn muốn tài chính của mình ổn định đến mức nào?"},
    {"id": 292, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Có điều gì bạn muốn thử dù người khác cho là điên rồ?"},
    {"id": 293, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn muốn sự nghiệp của mình phát triển theo hướng nào?"},
    {"id": 294, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Điều gì sẽ khiến bạn nói 'cuộc đời thật trọn vẹn'?"},
    {"id": 295, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn muốn dành phần đời còn lại để theo đuổi điều gì?"},
    {"id": 296, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Có truyền thống nào bạn muốn duy trì suốt đời?"},
    {"id": 297, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn muốn trở nên giỏi hơn ở lĩnh vực nào?"},
    {"id": 298, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Nếu thời gian không là vấn đề, bạn sẽ học gì?"},
    {"id": 299, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Bạn muốn một năm nữa nhìn lại và tự hào về điều gì?"},
    {"id": 300, "category": "Mơ ước & Tương lai", "emoji": "✨", "text": "Ước mơ nào bạn nghĩ chỉ cần một bước nữa là chạm tới?"},

    # --- Giá trị & Niềm tin (301–330) ---
    {"id": 301, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Điều gì bạn coi là 'không thể mua được bằng tiền'?"},
    {"id": 302, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Bạn ngưỡng mộ phẩm chất nào ở người khác nhất?"},
    {"id": 303, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Một cuộc sống 'đủ' với bạn là như thế nào?"},
    {"id": 304, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Bạn tin vào số phận hay tin mình tự định đoạt?"},
    {"id": 305, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Điều gì khiến bạn mất lòng tin vào một người?"},
    {"id": 306, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Bạn nghĩ điều gì làm nên một con người tử tế?"},
    {"id": 307, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Quy tắc sống nào bạn luôn tuân theo?"},
    {"id": 308, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Bạn đánh giá cao sự trung thực hay sự khéo léo hơn?"},
    {"id": 309, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Điều gì bạn nghĩ thế hệ trẻ đang dần đánh mất?"},
    {"id": 310, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Bạn định nghĩa tự do là gì?"},
    {"id": 311, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Có niềm tin nào của bạn đã thay đổi khi trưởng thành?"},
    {"id": 312, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Bạn nghĩ tiền bạc và hạnh phúc liên quan với nhau thế nào?"},
    {"id": 313, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Điều gì khiến bạn tôn trọng một người ngay lập tức?"},
    {"id": 314, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Bạn nghĩ điều gì là quan trọng để truyền lại cho đời sau?"},
    {"id": 315, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Công bằng với bạn có nghĩa là gì?"},
    {"id": 316, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Bạn sẵn sàng hi sinh điều gì vì điều mình tin?"},
    {"id": 317, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Điều gì bạn nghĩ là thước đo của một đời sống tốt?"},
    {"id": 318, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Bạn coi trọng trải nghiệm hay vật chất hơn?"},
    {"id": 319, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Có câu nói hay triết lý nào bạn lấy làm kim chỉ nam?"},
    {"id": 320, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Bạn nghĩ tha thứ là sức mạnh hay sự yếu đuối?"},
    {"id": 321, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Điều gì bạn không bao giờ thỏa hiệp về mặt đạo đức?"},
    {"id": 322, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Bạn có tin vào 'nhân quả' không?"},
    {"id": 323, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Điều gì khiến bạn cảm thấy cuộc sống có ý nghĩa?"},
    {"id": 324, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Theo bạn, thành công và hạnh phúc, cái nào quan trọng hơn?"},
    {"id": 325, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Có giá trị nào từ cha mẹ mà bạn muốn giữ lại?"},
    {"id": 326, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Bạn nghĩ điều gì khiến một mối quan hệ bền vững?"},
    {"id": 327, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Bạn coi trọng lý trí hay cảm xúc khi quyết định?"},
    {"id": 328, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Điều gì bạn nghĩ mọi người nên thử ít nhất một lần?"},
    {"id": 329, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Bạn tin con người vốn thiện hay phải học để tốt?"},
    {"id": 330, "category": "Giá trị & Niềm tin", "emoji": "🌟", "text": "Điều gì khiến bạn thấy biết ơn nhất trong đời?"},

    # --- Ký ức & Quá khứ (331–360) ---
    {"id": 331, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Mùi hương nào đưa bạn về tuổi thơ?"},
    {"id": 332, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Món ăn nào gợi nhớ nhà nhất với bạn?"},
    {"id": 333, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Trò chơi nào bạn mê nhất hồi nhỏ?"},
    {"id": 334, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Kỳ nghỉ hè đáng nhớ nhất của bạn là gì?"},
    {"id": 335, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Bạn từng thần tượng ai khi còn bé?"},
    {"id": 336, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Có thầy cô nào để lại dấu ấn lớn trong bạn?"},
    {"id": 337, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Kỷ niệm vui nhất thời đi học của bạn là gì?"},
    {"id": 338, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Bạn từng ước mơ làm nghề gì khi còn nhỏ?"},
    {"id": 339, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Có người bạn thời thơ ấu nào bạn vẫn nhớ?"},
    {"id": 340, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Lần đầu tiên bạn thấy mình 'đã lớn' là khi nào?"},
    {"id": 341, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Bạn từng làm điều gì khiến bố mẹ tự hào?"},
    {"id": 342, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Có nơi chốn nào trong quá khứ bạn muốn ghé lại?"},
    {"id": 343, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Bài hát nào gắn với một giai đoạn của đời bạn?"},
    {"id": 344, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Bạn nhớ nhất điều gì về ông bà mình?"},
    {"id": 345, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Kỷ niệm gia đình nào khiến bạn cười mỗi khi nhớ lại?"},
    {"id": 346, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Có quyết định nào hồi trẻ đã thay đổi đời bạn?"},
    {"id": 347, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Bạn từng vượt qua nỗi sợ nào đáng nhớ?"},
    {"id": 348, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Món quà nào bạn nhớ nhất từng được tặng?"},
    {"id": 349, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Có khoảnh khắc nào bạn ước quay lại để nói lời cảm ơn?"},
    {"id": 350, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Bạn nhớ điều gì về ngôi nhà tuổi thơ?"},
    {"id": 351, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Lần đầu xa nhà bạn cảm thấy thế nào?"},
    {"id": 352, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Có thất bại nào hồi trẻ giờ bạn thấy biết ơn?"},
    {"id": 353, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Bạn từng có 'mối tình thầm' nào không?"},
    {"id": 354, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Kỷ niệm nào về một mùa Tết khiến bạn ấm lòng?"},
    {"id": 355, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Bạn học được bài học lớn nào từ một sai lầm cũ?"},
    {"id": 356, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Có cuốn sách hay bộ phim thời trẻ nào ảnh hưởng đến bạn?"},
    {"id": 357, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Bạn nhớ cảm giác nào của tuổi mới lớn nhất?"},
    {"id": 358, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Lần đầu tự kiếm được tiền bạn đã làm gì?"},
    {"id": 359, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Có lời khuyên nào hồi xưa giờ bạn mới thấy đúng?"},
    {"id": 360, "category": "Ký ức & Quá khứ", "emoji": "💭", "text": "Khoảnh khắc nào khiến bạn trưởng thành nhanh nhất?"},

    # --- Gia đình & Bạn bè (361–385) ---
    {"id": 361, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Truyền thống gia đình nào bạn yêu thích nhất?"},
    {"id": 362, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Bạn giống bố hay mẹ nhiều hơn, ở điểm gì?"},
    {"id": 363, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Có điều gì bạn muốn nói với bố mẹ mà chưa nói được?"},
    {"id": 364, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Người thân nào bạn muốn gần gũi hơn?"},
    {"id": 365, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Bạn học được điều gì quý giá từ ông bà?"},
    {"id": 366, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Vai trò của bạn trong gia đình là gì?"},
    {"id": 367, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Bạn muốn xây dựng gia đình của mình khác đi như thế nào?"},
    {"id": 368, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Người bạn nào hiểu bạn nhất, vì sao?"},
    {"id": 369, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Bạn trân trọng điều gì nhất ở những người bạn thân?"},
    {"id": 370, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Có mâu thuẫn gia đình nào bạn mong được hàn gắn?"},
    {"id": 371, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Bạn thể hiện tình cảm với gia đình theo cách nào?"},
    {"id": 372, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Ai là người bạn luôn gọi đầu tiên khi có chuyện?"},
    {"id": 373, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Bạn muốn con cái (nếu có) nhớ về mình như thế nào?"},
    {"id": 374, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Có thói quen gia đình nào bạn muốn truyền lại?"},
    {"id": 375, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Bạn thấy tình bạn thay đổi thế nào khi trưởng thành?"},
    {"id": 376, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Người nào ngoài gia đình mà bạn coi như người thân?"},
    {"id": 377, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Bạn muốn dành nhiều thời gian hơn cho ai?"},
    {"id": 378, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Có lời xin lỗi nào bạn còn nợ ai đó không?"},
    {"id": 379, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Bạn ngưỡng mộ điều gì ở cách bố mẹ đối xử với nhau?"},
    {"id": 380, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Bạn muốn các dịp sum họp gia đình diễn ra thế nào?"},
    {"id": 381, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Có người bạn cũ nào bạn muốn nối lại liên lạc?"},
    {"id": 382, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Bạn nghĩ điều gì tạo nên một tình bạn bền chặt?"},
    {"id": 383, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Bạn muốn được gia đình ủng hộ về điều gì hơn?"},
    {"id": 384, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Vai trò 'người lớn' trong gia đình có khiến bạn áp lực không?"},
    {"id": 385, "category": "Gia đình & Bạn bè", "emoji": "🏡", "text": "Bạn biết ơn ai nhất trong cuộc đời, vì điều gì?"},

    # --- Cuộc sống hàng ngày (386–415) ---
    {"id": 386, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Khoảnh khắc nào trong ngày bạn thấy bình yên nhất?"},
    {"id": 387, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Bạn thích buổi sáng hay buổi tối hơn?"},
    {"id": 388, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Thức uống nào giúp bạn bắt đầu ngày mới?"},
    {"id": 389, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Bạn nạp lại năng lượng bằng cách nào?"},
    {"id": 390, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Việc nhỏ nào có thể khiến bạn vui cả ngày?"},
    {"id": 391, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Bạn thích không gian sống gọn gàng hay thoải mái bừa bộn?"},
    {"id": 392, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Có 'nghi thức' nào mỗi ngày mà bạn không thể thiếu?"},
    {"id": 393, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Bạn xử lý căng thẳng bằng cách nào?"},
    {"id": 394, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Bữa sáng lý tưởng của bạn là gì?"},
    {"id": 395, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Bạn thích làm việc trong yên tĩnh hay có nhạc?"},
    {"id": 396, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Cuối ngày bạn thích thư giãn bằng cách nào?"},
    {"id": 397, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Có thói quen nào giúp ích cho bạn mỗi ngày?"},
    {"id": 398, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Bạn thích cuối tuần năng động hay nghỉ ngơi?"},
    {"id": 399, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Món ăn 'an ủi tâm hồn' của bạn là gì?"},
    {"id": 400, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Bạn thấy mình làm việc hiệu quả nhất vào lúc nào?"},
    {"id": 401, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Có việc vặt nào bạn thấy thư giãn khi làm?"},
    {"id": 402, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Bạn thích vận động bằng cách nào nhất?"},
    {"id": 403, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Một ngày nghỉ hoàn hảo của bạn diễn ra thế nào?"},
    {"id": 404, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Bạn dành thời gian rảnh cho điều gì nhiều nhất?"},
    {"id": 405, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Có thói quen xấu nào bạn muốn thay đổi?"},
    {"id": 406, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Bạn thích nấu ăn hay được nấu cho?"},
    {"id": 407, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Điều gì giúp giấc ngủ của bạn ngon hơn?"},
    {"id": 408, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Bạn thích sự ngẫu hứng hay có kế hoạch?"},
    {"id": 409, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Có 'niềm vui nhỏ' nào bạn hay tự thưởng cho mình?"},
    {"id": 410, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Ngày mưa bạn thích ở nhà hay ra ngoài?"},
    {"id": 411, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Mùa nào trong năm bạn thích nhất, vì sao?"},
    {"id": 412, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Bạn bắt đầu ngày mới bằng việc gì đầu tiên?"},
    {"id": 413, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Có bài hát nào bạn hay nghe khi làm việc?"},
    {"id": 414, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Bạn thích trà, cà phê hay loại nước nào?"},
    {"id": 415, "category": "Cuộc sống hàng ngày", "emoji": "☀️", "text": "Điều gì khiến một ngày bình thường trở nên đẹp đẽ?"},

    # --- Tăng trưởng bản thân (416–440) ---
    {"id": 416, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Bạn đang cố gắng cải thiện điều gì ở bản thân?"},
    {"id": 417, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Cuốn sách nào đã thay đổi cách bạn suy nghĩ?"},
    {"id": 418, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Bạn học tốt nhất qua cách nào?"},
    {"id": 419, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Thói quen nào bạn tự hào vì đã xây dựng được?"},
    {"id": 420, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Bạn xử lý lời phê bình như thế nào?"},
    {"id": 421, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Điều gì bạn từng nghĩ không làm được nhưng đã làm?"},
    {"id": 422, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Bạn muốn bớt sợ điều gì hơn?"},
    {"id": 423, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Có kỹ năng mềm nào bạn muốn giỏi hơn?"},
    {"id": 424, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Bạn định nghĩa 'phiên bản tốt nhất của mình' thế nào?"},
    {"id": 425, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Điều gì thúc đẩy bạn cố gắng mỗi ngày?"},
    {"id": 426, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Bạn học được gì từ thất bại gần đây nhất?"},
    {"id": 427, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Có lời khuyên nào bạn muốn nói với bản thân 5 năm trước?"},
    {"id": 428, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Bạn muốn rèn luyện tính cách nào?"},
    {"id": 429, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Điều gì khiến bạn cảm thấy mình đang tiến bộ?"},
    {"id": 430, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Bạn vượt qua sự trì hoãn bằng cách nào?"},
    {"id": 431, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Có mục tiêu nào bạn đang âm thầm theo đuổi?"},
    {"id": 432, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Bạn muốn dành thời gian học gì cho bản thân?"},
    {"id": 433, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Điều gì khiến bạn bước ra khỏi vùng an toàn gần đây?"},
    {"id": 434, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Bạn nghĩ điểm mạnh lớn nhất của mình là gì?"},
    {"id": 435, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Bạn muốn cải thiện cách quản lý cảm xúc thế nào?"},
    {"id": 436, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Có thói quen nào bạn ngưỡng mộ ở người khác và muốn học?"},
    {"id": 437, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Bạn tự chăm sóc tinh thần mình bằng cách nào?"},
    {"id": 438, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Điều gì khiến bạn cảm thấy tự tin hơn?"},
    {"id": 439, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Bạn muốn năm nay trở thành người như thế nào?"},
    {"id": 440, "category": "Tăng trưởng bản thân", "emoji": "🚀", "text": "Bài học lớn nhất cuộc sống đã dạy bạn đến giờ là gì?"},

    # --- Vui & Sáng tạo (441–480) ---
    {"id": 441, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu được làm bất cứ nghề nào trong một ngày, bạn chọn nghề gì?"},
    {"id": 442, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Siêu năng lực nào bạn muốn có nhất?"},
    {"id": 443, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu trúng số, việc đầu tiên bạn làm là gì?"},
    {"id": 444, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Bạn muốn thử loại hình nghệ thuật nào?"},
    {"id": 445, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu là một nhân vật hoạt hình, bạn sẽ là ai?"},
    {"id": 446, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Bạn muốn du hành thời gian về quá khứ hay tới tương lai?"},
    {"id": 447, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu mở một quán, đó sẽ là quán gì?"},
    {"id": 448, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Bạn chọn sống ở biển hay trên núi?"},
    {"id": 449, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu được gặp một người nổi tiếng, bạn chọn ai?"},
    {"id": 450, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Món ăn nào bạn có thể ăn mãi không chán?"},
    {"id": 451, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu là một loài cây, bạn sẽ là cây gì?"},
    {"id": 452, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Bạn muốn có tài lẻ nào để 'khoe'?"},
    {"id": 453, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu được sống trong một bộ phim, bạn chọn phim nào?"},
    {"id": 454, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Bạn thích phiêu lưu hay nghỉ dưỡng khi đi du lịch?"},
    {"id": 455, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu được đặt tên cho một hòn đảo, bạn đặt là gì?"},
    {"id": 456, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Bạn muốn thử món ăn lạ nào của thế giới?"},
    {"id": 457, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu có robot làm một việc nhà, bạn chọn việc gì?"},
    {"id": 458, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Bạn muốn học điệu nhảy nào?"},
    {"id": 459, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu viết một bài hát, nó sẽ nói về điều gì?"},
    {"id": 460, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Bạn thích trò chơi board game nào nhất?"},
    {"id": 461, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu được sống một ngày là người khác, bạn chọn ai?"},
    {"id": 462, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Bạn muốn nuôi thú cưng gì, kể cả phi thực tế?"},
    {"id": 463, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu mở một triển lãm về đời mình, sẽ có gì trong đó?"},
    {"id": 464, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Bạn thích bất ngờ hay tự lên kế hoạch cho niềm vui?"},
    {"id": 465, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu có một điều ước (vui thôi), bạn ước gì?"},
    {"id": 466, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Bạn muốn thử môn thể thao mạo hiểm nào?"},
    {"id": 467, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu là đầu bếp, món 'tủ' của bạn là gì?"},
    {"id": 468, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Bạn thích trang trí nhà theo phong cách nào?"},
    {"id": 469, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu tổ chức một bữa tiệc trong mơ, nó sẽ thế nào?"},
    {"id": 470, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Bạn muốn học chơi nhạc cụ nào nhất?"},
    {"id": 471, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu lập một câu lạc bộ, đó sẽ là về điều gì?"},
    {"id": 472, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Bạn thích chụp ảnh về chủ đề gì?"},
    {"id": 473, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu có một ngày bí mật cho riêng mình, bạn làm gì?"},
    {"id": 474, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Bạn muốn sáng tạo điều gì nếu có khiếu nghệ thuật?"},
    {"id": 475, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu làm MC một chương trình, đó sẽ là show gì?"},
    {"id": 476, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Bạn thích sưu tầm thứ gì?"},
    {"id": 477, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu là một mùa trong năm, bạn là mùa nào?"},
    {"id": 478, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Bạn muốn thức dậy ở thành phố nào vào sáng mai?"},
    {"id": 479, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Nếu chỉ được nghe một thể loại nhạc cả đời, bạn chọn gì?"},
    {"id": 480, "category": "Vui & Sáng tạo", "emoji": "🎨", "text": "Bạn muốn để lại 'thông điệp vui' gì cho hậu thế?"},

    # --- Kỳ quặc & Thú vị (481–500) ---
    {"id": 481, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Bạn có nỗi sợ kỳ lạ nào không?"},
    {"id": 482, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Thói quen 'khó hiểu' nào của bạn ít ai biết?"},
    {"id": 483, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Bạn có mê tín điều gì buồn cười không?"},
    {"id": 484, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Món ăn kết hợp kỳ lạ nào bạn thực sự thích?"},
    {"id": 485, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Bạn từng tin điều ngớ ngẩn nào hồi nhỏ?"},
    {"id": 486, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Có việc nhỏ nào khiến bạn 'khó chịu' một cách vô lý?"},
    {"id": 487, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Bạn có hay nói chuyện với thú cưng hoặc đồ vật không?"},
    {"id": 488, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Tài lẻ vô dụng nhưng vui nào bạn đang sở hữu?"},
    {"id": 489, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Bạn có thói quen lạ nào khi căng thẳng không?"},
    {"id": 490, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Nếu được đặt một luật buồn cười cho cả nước, đó là gì?"},
    {"id": 491, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Bạn có 'thuyết' vui nào tin nửa đùa nửa thật?"},
    {"id": 492, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Món đồ vô dụng nào bạn vẫn giữ vì một lý do lạ?"},
    {"id": 493, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Bạn có cách ăn món nào 'khác người' không?"},
    {"id": 494, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Điều kỳ quặc nào khiến bạn thấy thỏa mãn lạ thường?"},
    {"id": 495, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Bạn từng làm điều gì 'dị' mà giờ thấy buồn cười?"},
    {"id": 496, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Có câu cửa miệng nào bạn hay nói không?"},
    {"id": 497, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Bạn có sắp xếp đồ đạc theo 'luật' kỳ lạ nào không?"},
    {"id": 498, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Nếu một ngày mọi quy tắc bị đảo lộn, bạn sẽ làm gì?"},
    {"id": 499, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Bạn có thói quen bí mật nào khi ở một mình?"},
    {"id": 500, "category": "Kỳ quặc & Thú vị", "emoji": "🦄", "text": "Điều 'dở hơi' nào về bản thân khiến bạn thấy đáng yêu?"},
]


QUESTION_BY_ID = {q['id']: q for q in QUESTIONS}

DEFAULT_STATE = {
    "partners": {"p1": "", "p2": ""},  # display names
    "used_qids": [],                    # questions already shown (avoid repeats)
    "current": None,                    # active round {date,qid,answers,revealed}
    "history": [],                      # archived rounds [{date,qid,answers}]
    "asked": [],                        # legacy explore-mode marks
    "subs": {"p1": [], "p2": []},       # web-push subscriptions per partner
    "last_morning_sent": "",            # date the morning push was last sent
}


# ── Storage backend ──────────────────────────────────────────────
# On free hosts (Render) the filesystem is ephemeral and wiped when the
# instance sleeps, so a JSON file would lose data between visits. If an
# Upstash Redis REST endpoint is configured, we persist there instead.
# Locally (no env vars) we fall back to a JSON file.
import urllib.request

UPSTASH_URL = os.environ.get('UPSTASH_REDIS_REST_URL', '').rstrip('/')
UPSTASH_TOKEN = os.environ.get('UPSTASH_REDIS_REST_TOKEN', '')
STATE_KEY = os.environ.get('STATE_KEY', 'four_state')
USE_REDIS = bool(UPSTASH_URL and UPSTASH_TOKEN)


def _redis_cmd(cmd):
    """Run one Upstash REST command (list form), return 'result'."""
    req = urllib.request.Request(
        UPSTASH_URL,
        data=json.dumps(cmd).encode('utf-8'),
        headers={'Authorization': f'Bearer {UPSTASH_TOKEN}',
                 'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r).get('result')


def _migrate(state):
    for k, v in DEFAULT_STATE.items():
        state.setdefault(k, json.loads(json.dumps(v)))
    return state


def load_state():
    state = {}
    if USE_REDIS:
        try:
            raw = _redis_cmd(['GET', STATE_KEY])
            if raw:
                state = json.loads(raw)
        except Exception as e:
            print('[storage] redis load failed:', e)
    elif os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
    return _migrate(state)


def save_state(state):
    if USE_REDIS:
        try:
            _redis_cmd(['SET', STATE_KEY, json.dumps(state, ensure_ascii=False)])
            return
        except Exception as e:
            print('[storage] redis save failed:', e)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def today_str():
    from datetime import date
    return date.today().isoformat()


def _make_round(state):
    """Create a fresh round with a question not used recently."""
    used = set(state['used_qids'])
    pool = [q for q in QUESTIONS if q['id'] not in used]
    if not pool:                          # all used -> recycle
        state['used_qids'] = []
        pool = QUESTIONS[:]
    q = random.choice(pool)
    state['used_qids'].append(q['id'])
    return {"date": today_str(), "qid": q['id'],
            "answers": {"p1": "", "p2": ""}, "revealed": False}


def _archive(state, rnd):
    """Move a completed (revealed, answered) round into history."""
    if rnd and rnd.get('revealed') and any(rnd['answers'][p].strip() for p in ('p1', 'p2')):
        state['history'].append({"date": rnd['date'], "qid": rnd['qid'],
                                 "answers": rnd['answers']})


def ensure_today_question(state):
    """Return the active round, creating/rolling it over as needed.

    - First ever use -> new round.
    - New day -> archive the (revealed) previous round, start a fresh one
      (this drives the daily morning question).
    """
    # one-time migration from the old per-day model
    if state.get('daily'):
        for d in sorted(state['daily'].keys()):
            day = state['daily'][d]
            if day.get('revealed'):
                state['history'].append({"date": d, "qid": day['qid'],
                                         "answers": day['answers']})
        last = sorted(state['daily'].keys())[-1]
        ld = state['daily'][last]
        state['current'] = {"date": last, "qid": ld['qid'],
                            "answers": ld['answers'], "revealed": ld['revealed']}
        state['daily'] = {}
        save_state(state)

    cur = state.get('current')
    if not cur:
        state['current'] = _make_round(state)
        save_state(state)
    elif cur['date'] != today_str():
        _archive(state, cur)
        state['current'] = _make_round(state)
        save_state(state)
    return state['current']


def public_today(state, rnd, who=None):
    """Build the round payload. Hide partner answers unless revealed."""
    q = QUESTION_BY_ID[rnd['qid']]
    p1_done = bool(rnd['answers']['p1'].strip())
    p2_done = bool(rnd['answers']['p2'].strip())
    payload = {
        "date": rnd['date'],
        "question": q,
        "p1_done": p1_done,
        "p2_done": p2_done,
        "both_done": p1_done and p2_done,
        "revealed": rnd['revealed'],
        "partners": state['partners'],
        "history_count": len(state.get('history', [])),
    }
    if rnd['revealed']:
        payload['answers'] = rnd['answers']
    return payload


# ── Web push helpers ─────────────────────────────────────────────
def send_push(subscription, title, body, url='/'):
    """Send one push. Returns True on success, False if expired/failed."""
    if not _PUSH_OK:
        return False
    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps({"title": title, "body": body, "url": url}),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": VAPID_SUBJECT},
            timeout=10,
        )
        return True
    except WebPushException as e:
        # 404/410 -> subscription gone; signal removal
        code = getattr(getattr(e, 'response', None), 'status_code', None)
        if code in (404, 410):
            return None
        return False
    except Exception:
        return False


def push_to_roles(state, roles, title, body, url='/'):
    """Send to all subscriptions of the given roles; prune dead ones."""
    changed = False
    for role in roles:
        kept = []
        for sub in state['subs'].get(role, []):
            res = send_push(sub, title, body, url)
            if res is None:        # expired -> drop
                changed = True
                continue
            kept.append(sub)
        state['subs'][role] = kept
    if changed:
        save_state(state)


def send_morning(state=None):
    """Send the daily morning notification (idempotent per day)."""
    state = state or load_state()
    d = today_str()
    if state.get('last_morning_sent') == d:
        return {"sent": False, "reason": "already sent today"}
    ensure_today_question(state)
    push_to_roles(state, ['p1', 'p2'],
                  'Chào buổi sáng ❤️',
                  'Câu hỏi hôm nay đã sẵn sàng. Cùng trả lời nhé!',
                  '/')
    state = load_state()
    state['last_morning_sent'] = d
    save_state(state)
    return {"sent": True}


@app.route('/')
def index():
    return render_template('index.html', total=len(QUESTIONS))


# ── PWA: service worker (root scope) + manifest ──────────────────
@app.route('/sw.js')
def service_worker():
    resp = send_from_directory(os.path.join(BASE_DIR, 'static'), 'sw.js')
    resp.headers['Service-Worker-Allowed'] = '/'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


@app.route('/manifest.json')
def manifest():
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'manifest.json')


# ── Push subscription endpoints ──────────────────────────────────
@app.route('/api/vapid-public')
def vapid_public():
    return jsonify({"key": VAPID_PUBLIC_KEY, "enabled": _PUSH_OK})


@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    data = request.get_json() or {}
    who = data.get('who')
    sub = data.get('subscription')
    if who not in ('p1', 'p2') or not sub or not sub.get('endpoint'):
        return jsonify({"error": "thiếu thông tin"}), 400
    state = load_state()
    subs = state['subs'].setdefault(who, [])
    if not any(s.get('endpoint') == sub['endpoint'] for s in subs):
        subs.append(sub)
        save_state(state)
    return jsonify({"ok": True})


@app.route('/api/test-push', methods=['POST'])
def test_push():
    data = request.get_json() or {}
    who = data.get('who')
    if who not in ('p1', 'p2'):
        return jsonify({"error": "thiếu who"}), 400
    state = load_state()
    push_to_roles(state, [who], 'Thông báo thử ❤️',
                  'Tuyệt! Bạn sẽ nhận được nhắc nhở mỗi sáng.', '/')
    return jsonify({"ok": True})


# ── Cron endpoint for morning notification (external scheduler) ──
@app.route('/cron/morning', methods=['GET', 'POST'])
def cron_morning():
    if request.args.get('key') != CRON_SECRET:
        return jsonify({"error": "unauthorized"}), 401
    return jsonify(send_morning())


# ── Partner setup ────────────────────────────────────────────────
@app.route('/api/partners', methods=['GET', 'POST'])
def partners():
    state = load_state()
    if request.method == 'POST':
        data = request.get_json() or {}
        who = data.get('who')             # 'p1' or 'p2'
        name = (data.get('name') or '').strip()[:30]
        if who in ('p1', 'p2') and name:
            state['partners'][who] = name
            save_state(state)
    return jsonify({"partners": state['partners']})


# ── Question flow ────────────────────────────────────────────────
@app.route('/api/today')
def today():
    state = load_state()
    rnd = ensure_today_question(state)
    who = request.args.get('who')
    return jsonify(public_today(state, rnd, who))


@app.route('/api/answer', methods=['POST'])
def answer():
    data = request.get_json() or {}
    who = data.get('who')
    text = (data.get('text') or '').strip()
    if who not in ('p1', 'p2') or not text:
        return jsonify({"error": "thiếu thông tin"}), 400
    state = load_state()
    rnd = ensure_today_question(state)
    was_done = bool(rnd['answers'][who].strip())
    rnd['answers'][who] = text
    save_state(state)

    # Notify the other partner (only on first answer, not edits)
    if not was_done:
        other_role = 'p2' if who == 'p1' else 'p1'
        my_name = state['partners'].get(who) or ('Người 1' if who == 'p1' else 'Người 2')
        if all(rnd['answers'][p].strip() for p in ('p1', 'p2')):
            push_to_roles(state, [other_role], 'Cả hai đã trả lời! 🎉',
                          'Mở app để cùng xem câu trả lời của nhau nhé ❤️', '/')
        else:
            push_to_roles(state, [other_role], f'{my_name} đã trả lời 💌',
                          'Tới lượt bạn rồi! Mở app để trả lời nhé.', '/')

    return jsonify(public_today(state, rnd, who))


@app.route('/api/reveal', methods=['POST'])
def reveal():
    state = load_state()
    rnd = ensure_today_question(state)
    if not all(rnd['answers'][p].strip() for p in ('p1', 'p2')):
        return jsonify({"error": "Cả hai cần trả lời trước khi mở"}), 400
    rnd['revealed'] = True
    save_state(state)
    return jsonify(public_today(state, rnd))


@app.route('/api/new-question', methods=['POST'])
def new_question():
    """Swap the CURRENT question for another (before reveal); clears answers."""
    state = load_state()
    rnd = ensure_today_question(state)
    if rnd['revealed']:
        return jsonify({"error": "Câu hỏi đã được mở, không thể đổi nữa"}), 400
    cur_id = rnd['qid']
    used = set(state['used_qids'])
    pool = [q for q in QUESTIONS if q['id'] not in used and q['id'] != cur_id]
    if not pool:
        pool = [q for q in QUESTIONS if q['id'] != cur_id] or QUESTIONS[:]
    q = random.choice(pool)
    if q['id'] not in state['used_qids']:
        state['used_qids'].append(q['id'])
    rnd['qid'] = q['id']
    rnd['answers'] = {"p1": "", "p2": ""}
    rnd['revealed'] = False
    save_state(state)
    return jsonify(public_today(state, rnd))


@app.route('/api/next', methods=['POST'])
def next_question():
    """After reveal: archive the round and start a brand-new one (same day)."""
    state = load_state()
    rnd = ensure_today_question(state)
    if not rnd['revealed']:
        return jsonify({"error": "Cần mở câu trả lời trước khi sang câu mới"}), 400
    _archive(state, rnd)
    state['current'] = _make_round(state)
    save_state(state)
    return jsonify(public_today(state, state['current']))


# ── History ──────────────────────────────────────────────────────
@app.route('/api/history')
def history():
    state = load_state()
    out = []
    for h in reversed(state.get('history', [])):
        q = QUESTION_BY_ID.get(h['qid'])
        if not q:
            continue
        out.append({"date": h['date'], "question": q, "answers": h['answers']})
    return jsonify({"history": out, "partners": state['partners']})


# ── Legacy explore mode ──────────────────────────────────────────
@app.route('/api/question')
def get_question():
    state = load_state()
    asked_ids = set(state['asked'])
    available = [q for q in QUESTIONS if q['id'] not in asked_ids]
    if not available:
        return jsonify({'done': True, 'total': len(QUESTIONS)})
    q = random.choice(available)
    return jsonify({
        'done': False, 'question': q, 'remaining': len(available),
        'total': len(QUESTIONS), 'asked_count': len(QUESTIONS) - len(available),
    })


@app.route('/api/mark', methods=['POST'])
def mark_asked():
    data = request.get_json()
    qid = data.get('id')
    state = load_state()
    if qid not in state['asked']:
        state['asked'].append(qid)
        save_state(state)
    return jsonify({'success': True})


@app.route('/api/reset', methods=['POST'])
def reset():
    state = load_state()
    state['asked'] = []
    save_state(state)
    return jsonify({'success': True})


# ── Optional in-process scheduler (for always-on hosts / VPS) ────
# Set ENABLE_SCHEDULER=1 and MORNING_HOUR (default 8) to use.
# On hosts that sleep (e.g. Render free), use an external cron hitting
# /cron/morning?key=CRON_SECRET instead — it's more reliable.
def _start_scheduler():
    if os.environ.get('ENABLE_SCHEDULER') != '1':
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except Exception:
        print('[scheduler] APScheduler not installed; skipping')
        return
    hour = int(os.environ.get('MORNING_HOUR', '8'))
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(lambda: send_morning(), 'cron', hour=hour, minute=0)
    sched.start()
    print(f'[scheduler] morning push scheduled daily at {hour:02d}:00')


_start_scheduler()


if __name__ == '__main__':
    import socket, sys
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = '127.0.0.1'
    print(f"\n  App dang chay!")
    print(f"  May tinh  : http://localhost:5000")
    print(f"  Dien thoai: http://{local_ip}:5000\n")
    app.run(debug=False, host='0.0.0.0', port=5000)

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
]


QUESTION_BY_ID = {q['id']: q for q in QUESTIONS}

DEFAULT_STATE = {
    "partners": {"p1": "", "p2": ""},  # display names
    "used_qids": [],                    # questions already used as daily question
    "daily": {},                        # date -> {qid, answers:{p1,p2}, revealed}
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


def ensure_today_question(state):
    """Pick a shared question for today if not already chosen."""
    d = today_str()
    if d not in state['daily']:
        used = set(state['used_qids'])
        pool = [q for q in QUESTIONS if q['id'] not in used]
        if not pool:                      # all used -> recycle
            state['used_qids'] = []
            pool = QUESTIONS[:]
        q = random.choice(pool)
        state['daily'][d] = {"qid": q['id'], "answers": {"p1": "", "p2": ""}, "revealed": False}
        state['used_qids'].append(q['id'])
        save_state(state)
    return state['daily'][d]


def public_today(state, day):
    """Build the today payload. Hide partner answers unless revealed."""
    q = QUESTION_BY_ID[day['qid']]
    p1_done = bool(day['answers']['p1'].strip())
    p2_done = bool(day['answers']['p2'].strip())
    both_done = p1_done and p2_done
    payload = {
        "date": today_str(),
        "question": q,
        "p1_done": p1_done,
        "p2_done": p2_done,
        "both_done": both_done,
        "revealed": day['revealed'],
        "partners": state['partners'],
    }
    if day['revealed']:
        payload['answers'] = day['answers']
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


# ── Daily question flow ──────────────────────────────────────────
@app.route('/api/today')
def today():
    state = load_state()
    day = ensure_today_question(state)
    return jsonify(public_today(state, day))


@app.route('/api/answer', methods=['POST'])
def answer():
    data = request.get_json() or {}
    who = data.get('who')
    text = (data.get('text') or '').strip()
    if who not in ('p1', 'p2') or not text:
        return jsonify({"error": "thiếu thông tin"}), 400
    state = load_state()
    day = ensure_today_question(state)
    was_done = bool(day['answers'][who].strip())
    day['answers'][who] = text
    save_state(state)

    # Notify the other partner (only on first answer, not edits)
    if not was_done:
        other_role = 'p2' if who == 'p1' else 'p1'
        my_name = state['partners'].get(who) or ('Người 1' if who == 'p1' else 'Người 2')
        if all(day['answers'][p].strip() for p in ('p1', 'p2')):
            push_to_roles(state, [other_role], 'Cả hai đã trả lời! 🎉',
                          'Mở app để cùng xem câu trả lời của nhau nhé ❤️', '/')
        else:
            push_to_roles(state, [other_role], f'{my_name} đã trả lời 💌',
                          'Tới lượt bạn rồi! Mở app để trả lời nhé.', '/')

    return jsonify(public_today(state, day))


@app.route('/api/reveal', methods=['POST'])
def reveal():
    state = load_state()
    day = ensure_today_question(state)
    both = all(day['answers'][p].strip() for p in ('p1', 'p2'))
    if not both:
        return jsonify({"error": "Cả hai cần trả lời trước khi mở"}), 400
    day['revealed'] = True
    save_state(state)
    return jsonify(public_today(state, day))


@app.route('/api/new-question', methods=['POST'])
def new_question():
    """Swap today's question for a different one (clears today's answers)."""
    state = load_state()
    d = today_str()
    day = ensure_today_question(state)
    if day['revealed']:
        return jsonify({"error": "Câu hỏi hôm nay đã được mở, không thể đổi nữa"}), 400
    current = day['qid']
    used = set(state['used_qids'])
    pool = [q for q in QUESTIONS if q['id'] not in used and q['id'] != current]
    if not pool:                                  # all used -> any other question
        pool = [q for q in QUESTIONS if q['id'] != current] or QUESTIONS[:]
    q = random.choice(pool)
    state['daily'][d] = {"qid": q['id'], "answers": {"p1": "", "p2": ""}, "revealed": False}
    if q['id'] not in state['used_qids']:
        state['used_qids'].append(q['id'])
    save_state(state)
    return jsonify(public_today(state, state['daily'][d]))


# ── History ──────────────────────────────────────────────────────
@app.route('/api/history')
def history():
    state = load_state()
    out = []
    for d in sorted(state['daily'].keys(), reverse=True):
        day = state['daily'][d]
        if d == today_str() and not day['revealed']:
            continue                       # don't leak today before reveal
        if not day['revealed']:
            continue
        out.append({
            "date": d,
            "question": QUESTION_BY_ID[day['qid']],
            "answers": day['answers'],
        })
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

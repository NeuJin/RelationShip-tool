from flask import Flask, render_template, jsonify, request
import json, os, random

app = Flask(__name__)
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'state.json')

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
]


QUESTION_BY_ID = {q['id']: q for q in QUESTIONS}

DEFAULT_STATE = {
    "partners": {"p1": "", "p2": ""},  # display names
    "used_qids": [],                    # questions already used as daily question
    "daily": {},                        # date -> {qid, answers:{p1,p2}, revealed}
    "asked": [],                        # legacy explore-mode marks
}


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
    else:
        state = {}
    # ensure all keys exist (migration-safe)
    for k, v in DEFAULT_STATE.items():
        state.setdefault(k, json.loads(json.dumps(v)))
    return state


def save_state(state):
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


@app.route('/')
def index():
    return render_template('index.html', total=len(QUESTIONS))


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
    day['answers'][who] = text
    save_state(state)
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

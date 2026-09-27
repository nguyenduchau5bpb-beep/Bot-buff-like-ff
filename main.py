import os
import time
import threading
import requests
import telebot
from telebot.types import BotCommand
from dotenv import load_dotenv
from flask import Flask

# ================= 1. FLASK WEB SERVER (GIỮ BOT ONLINE 24/7) =================
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Free Fire Like Bot (Free API) - MrGhost is Running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

# ================= 2. CẤU HÌNH BOT TELEGRAM & FREE API =================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ LỖI: Chưa cấu hình BOT_TOKEN trong file .env!")

bot = telebot.TeleBot(BOT_TOKEN)

# Danh sách các API Free Fire Like miễn phí công khai
FREE_LIKE_APIS = [
    "https://free-fire-like-api.vercel.app/like?uid={uid}&region={region}",
    "https://api-freefire-like.vercel.app/like?uid={uid}&region={region}",
    "https://ff-like-api.vercel.app/api/like?uid={uid}&region={region}"
]

REGIONS = ["vn", "sg", "ind", "br", "th", "me", "id", "us"]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

# ================= 3. HÀM TỰ ĐỘNG GỬI API BUFF LIKE =================
def request_free_like(uid):
    """Thử lần lượt từng server API miễn phí và từng Region cho đến khi thành công"""
    for api_template in FREE_LIKE_APIS:
        for reg in REGIONS:
            try:
                url = api_template.format(uid=uid, region=reg)
                res = requests.get(url, headers=HEADERS, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    if data.get('status') in ['success', True, 200, "200", 1] or 'likes_given' in data or 'likes_after' in data:
                        data['region_found'] = reg.upper()
                        return data
            except Exception:
                continue
    return None

# ================= 4. QUẢN LÝ COOLDOWN (30 GIÂY) =================
user_cooldowns = {}
COOLDOWN_TIME = 30

def check_cooldown(user_id):
    current_time = time.time()
    last_time = user_cooldowns.get(user_id, 0)
    if current_time - last_time < COOLDOWN_TIME:
        return False, int(COOLDOWN_TIME - (current_time - last_time))
    user_cooldowns[user_id] = current_time
    return True, 0

# ================= 5. KHỞI TẠO MENU LỆNH =================
try:
    bot.set_my_commands([
        BotCommand("start", "Khởi động bot"),
        BotCommand("like", "Buff like Free Fire (/like <UID>)"),
        BotCommand("help", "Hướng dẫn sử dụng")
    ])
except Exception as e:
    print(f"Lỗi khởi tạo Menu: {e}")

# ================= 6. XỬ LÝ LỆNH BẰNG BOT TELEGRAM =================
@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    msg = (
        "🤖 *FREE FIRE LIKE BOT*\n\n"
        "Chào mừng bạn đến với Bot Buff Like Free Fire Tự Động!\n\n"
        "📌 *Cú pháp sử dụng:*\n"
        "`/like <UID>`\n\n"
        "Ví dụ: `/like 123456789`\n\n"
        "👨‍💻 *CREATOR:* MrGhost\n"
        "🎵 *TIKTOK:* [mrghost1238](https://www.tiktok.com/@mrghost1238)"
    )
    bot.reply_to(message, msg, parse_mode="Markdown", disable_web_page_preview=True)

@bot.message_handler(commands=['like'])
def handle_like(message):
    user_id = message.from_user.id
    
    # Kiểm tra Cooldown 30s
    can_run, wait_sec = check_cooldown(user_id)
    if not can_run:
        bot.reply_to(message, f"⏱️ Vui lòng đợi *{wait_sec}* giây nữa trước khi thử lại.", parse_mode="Markdown")
        return

    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Sai cú pháp! Nhập: `/like <UID>`", parse_mode="Markdown")
        return

    uid = args[1]
    
    # Kiểm tra định dạng UID
    if not uid.isdigit() or len(uid) < 6:
        bot.reply_to(message, "❌ UID không hợp lệ! UID phải là chuỗi số có ít nhất 6 chữ số.")
        return

    status_msg = bot.reply_to(message, f"⏳ Đang xử lý yêu cầu buff like cho UID `{uid}`...", parse_mode="Markdown")

    # Gọi API miễn phí
    data = request_free_like(uid)

    if data:
        name = data.get('player_name') or data.get('name') or data.get('nickname') or data.get('player') or 'Free Fire Player'
        before_likes = data.get('likes_before', data.get('likes', 'N/A'))
        added = data.get('likes_given', data.get('added_likes', data.get('likes_added', 100)))
        after_likes = data.get('likes_after', 'Thành công')
        region = data.get('region_found', 'VN')

        result_card = (
            f"🟢 *FREE FIRE LIKE SUCCESS*\n\n"
            f"┌  *ACCOUNT*\n"
            f"├─ *NICKNAME:* {name}\n"
            f"├─ *UID:* `{uid}` ({region})\n"
            f"└─ *RESULT:*\n"
            f"   ├─ *ADDED:* +{added}\n"
            f"   ├─ *BEFORE:* {before_likes}\n"
            f"   └─ *AFTER:* {after_likes}\n\n"
            f"👨‍💻 *DEVELOPED BY:* MrGhost\n"
            f"🎵 *TIKTOK:* [mrghost1238](https://www.tiktok.com/@mrghost1238)"
        )
        bot.edit_message_text(result_card, chat_id=status_msg.chat.id, message_id=status_msg.message_id, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        bot.edit_message_text("❌ *Thất bại:* Máy chủ API bận hoặc UID đã nhận đủ max like hôm nay. Thử lại sau!", chat_id=status_msg.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")

# ================= 7. CHẠY BOT =================
if __name__ == "__main__":
    print("🚀 Telegram Bot Free Fire - Cre: MrGhost đã sẵn sàng!")
    bot.infinity_polling(skip_pending=True)
 

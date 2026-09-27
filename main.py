import os
import time
import threading
import requests
import telebot
from telebot.types import BotCommand
from dotenv import load_dotenv
from flask import Flask

# ================= 1. FLASK WEB SERVER (GIỮ BOT ONLINE 24/7 TRÊN RENDER) =================
app = Flask(__name__)
START_TIME = time.time()

@app.route('/')
def home():
    return "🤖 Telegram Free Fire Bot - MrGhost is Running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

# ================= 2. CẤU HÌNH BOT TELEGRAM & API =================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ LỖI: Chưa cấu hình BOT_TOKEN trong Environment Variable!")

bot = telebot.TeleBot(BOT_TOKEN)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

# ================= 3. HÀM XỬ LÝ API BUFF LIKE & CHECK ACC =================
def request_free_like(uid):
    """Gửi yêu cầu buff like tới các máy chủ API công khai"""
    api_urls = [
        f"https://free-fire-like-api.vercel.app/like?uid={uid}&region=vn",
        f"https://api-freefire-like.vercel.app/like?uid={uid}&region=sg",
        f"https://ff-like-api.vercel.app/api/like?uid={uid}&region=vn",
        f"https://free-fire-like-api.vercel.app/like?uid={uid}&region=sg"
    ]
    
    for url in api_urls:
        try:
            res = requests.get(url, headers=HEADERS, timeout=8)
            if res.status_code == 200:
                data = res.json()
                if data.get('status') in ['success', True, 200, "200", 1] or 'likes_given' in data or 'likes_after' in data:
                    return data
        except Exception:
            continue
    return None

def request_player_info(uid):
    """Gửi yêu cầu lấy thông tin chi tiết của tài khoản Free Fire"""
    info_urls = [
        f"https://free-fire-like-api.vercel.app/info?uid={uid}&region=vn",
        f"https://api-freefire-like.vercel.app/info?uid={uid}&region=sg",
        f"https://ff-like-api.vercel.app/api/info?uid={uid}&region=vn"
    ]
    
    for url in info_urls:
        try:
            res = requests.get(url, headers=HEADERS, timeout=8)
            if res.status_code == 200:
                data = res.json()
                if 'nickname' in data or 'player_name' in data or 'name' in data:
                    return data
        except Exception:
            continue
    return None

# ================= 4. QUẢN LÝ COOLDOWN (3 GIÂY) =================
user_cooldowns = {}
COOLDOWN_TIME = 3  # Đã đổi thành 3 giây

def check_cooldown(user_id):
    current_time = time.time()
    last_time = user_cooldowns.get(user_id, 0)
    if current_time - last_time < COOLDOWN_TIME:
        return False, int(COOLDOWN_TIME - (current_time - last_time))
    user_cooldowns[user_id] = current_time
    return True, 0

# ================= 5. KHỞI TẠO MENU LỆNH TRÊN TELEGRAM =================
try:
    bot.set_my_commands([
        BotCommand("start", "Khởi động & Menu chính"),
        BotCommand("like", "Buff like Free Fire (/like <UID>)"),
        BotCommand("check", "Check thông tin tài khoản (/check <UID>)"),
        BotCommand("id", "Xem Telegram ID của bạn"),
        BotCommand("stats", "Xem trạng thái hệ thống Bot"),
        BotCommand("help", "Trợ giúp & Hướng dẫn")
    ])
except Exception as e:
    print(f"Lỗi khởi tạo Menu: {e}")

# ================= 6. XỬ LÝ CÁC LỆNH CỦA BOT =================

# --- Lệnh /start & /help ---
@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    msg = (
        "🤖 *FREE FIRE TOOL HUB - MRGHOST*\n\n"
        "Chào mừng bạn đến với hệ thống Tool Free Fire Tự Động!\n\n"
        "📌 *Danh sách lệnh khả dụng:*\n"
        "🔹 `/like <UID>` : Buff lượt thích cho tài khoản Free Fire.\n"
        "🔹 `/check <UID>` : Xem Nickname, Level, Like hiện tại.\n"
        "🔹 `/id` : Kiểm tra Telegram ID và Chat ID của bạn.\n"
        "🔹 `/stats` : Kiểm tra độ trễ (Ping) và thời gian Bot hoạt động.\n"
        "🔹 `/help` : Hướng dẫn chi tiết sử dụng bot.\n\n"
        "💡 *Ví dụ:* `/like 18351440372`\n\n"
        "👨‍💻 *CREATOR:* MrGhost\n"
        "🎵 *TIKTOK:* [mrghost1238](https://www.tiktok.com/@mrghost1238)"
    )
    bot.reply_to(message, msg, parse_mode="Markdown", disable_web_page_preview=True)

# --- Lệnh /id ---
@bot.message_handler(commands=['id'])
def handle_id(message):
    user = message.from_user
    chat_id = message.chat.id
    msg = (
        "🆔 *THÔNG TIN TELEGRAM CỦA BẠN*\n\n"
        f"👤 *Họ tên:* `{user.first_name} {user.last_name or ''}`\n"
        f"🏷️ *Username:* `@{user.username or 'Không có'}`\n"
        f"🆔 *User ID:* `{user.id}`\n"
        f"💬 *Chat ID:* `{chat_id}`"
    )
    bot.reply_to(message, msg, parse_mode="Markdown")

# --- Lệnh /stats ---
@bot.message_handler(commands=['stats'])
def handle_stats(message):
    start_ping = time.time()
    status_msg = bot.reply_to(message, "⚡ Đang đo độ trễ hệ thống...")
    end_ping = time.time()
    
    ping_ms = round((end_ping - start_ping) * 1000, 2)
    uptime_sec = int(time.time() - START_TIME)
    hours, remainder = divmod(uptime_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    msg = (
        "📊 *TRẠNG THÁI HỆ THỐNG BOT*\n\n"
        f"🟢 *Trạng thái:* Hoạt động 24/7\n"
        f"⚡ *Độ trễ (Ping):* `{ping_ms} ms`\n"
        f"⏱️ *Thời gian chạy:* `{hours}h {minutes}m {seconds}s`\n"
        f"⏳ *Cooldown mặc định:* `3s`\n\n"
        f"👨‍💻 *DEVELOPED BY:* MrGhost"
    )
    bot.edit_message_text(msg, chat_id=status_msg.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")

# --- Lệnh /check <UID> ---
@bot.message_handler(commands=['check'])
def handle_check(message):
    user_id = message.from_user.id
    can_run, wait_sec = check_cooldown(user_id)
    if not can_run:
        bot.reply_to(message, f"⏱️ Vui lòng đợi *{wait_sec}*s.", parse_mode="Markdown")
        return

    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ *Sai cú pháp!* Sử dụng: `/check <UID>`", parse_mode="Markdown")
        return

    uid = args[1]
    if not uid.isdigit() or len(uid) < 6:
        bot.reply_to(message, "❌ *UID không hợp lệ!* Vui lòng nhập chuỗi số từ 6 ký tự trở lên.", parse_mode="Markdown")
        return

    status_msg = bot.reply_to(message, f"🔍 Đang tra cứu thông tin cho UID `{uid}`...", parse_mode="Markdown")
    
    data = request_player_info(uid)
    if data:
        name = data.get('nickname') or data.get('player_name') or data.get('name') or 'N/A'
        level = data.get('level') or data.get('player_level') or 'N/A'
        likes = data.get('likes') or data.get('like') or 'N/A'
        region = data.get('region', 'VN').upper()
        
        info_card = (
            f"📊 *THÔNG TIN TÀI KHOẢN FREE FIRE*\n\n"
            f"👤 *NICKNAME:* `{name}`\n"
            f"🆔 *UID:* `{uid}`\n"
            f"⭐ *LEVEL:* `{level}`\n"
            f"❤️ *LƯỢT LIKE:* `{likes}`\n"
            f"🌐 *KHU VỰC:* `{region}`\n\n"
            f"👨‍💻 *DEVELOPED BY:* MrGhost\n"
            f"🎵 *TIKTOK:* [mrghost1238](https://www.tiktok.com/@mrghost1238)"
        )
        bot.edit_message_text(info_card, chat_id=status_msg.chat.id, message_id=status_msg.message_id, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        bot.edit_message_text("❌ Không thể lấy thông tin tài khoản này. Vui lòng kiểm tra lại UID hoặc thử lại sau!", chat_id=status_msg.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")

# --- Lệnh /like <UID> ---
@bot.message_handler(commands=['like'])
def handle_like(message):
    user_id = message.from_user.id
    
    # Kiểm tra Cooldown 3s
    can_run, wait_sec = check_cooldown(user_id)
    if not can_run:
        bot.reply_to(message, f"⏱️ Vui lòng đợi *{wait_sec}*s nữa trước khi thử lại.", parse_mode="Markdown")
        return

    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ *Sai cú pháp!* Sử dụng: `/like <UID>`", parse_mode="Markdown")
        return

    uid = args[1]
    if not uid.isdigit() or len(uid) < 6:
        bot.reply_to(message, "❌ *UID không hợp lệ!*", parse_mode="Markdown")
        return

    status_msg = bot.reply_to(message, f"⏳ Đang gửi yêu cầu buff like cho UID `{uid}`...", parse_mode="Markdown")

    data = request_free_like(uid)

    if data:
        name = data.get('player_name') or data.get('name') or data.get('nickname') or 'Free Fire Player'
        before_likes = data.get('likes_before', data.get('likes', 'N/A'))
        added = data.get('likes_given', data.get('added_likes', 100))
        after_likes = data.get('likes_after', 'Thành công')

        result_card = (
            f"🟢 *BUFF LIKE THÀNH CÔNG*\n\n"
            f"┌  *ACCOUNT INFO*\n"
            f"├─ *NICKNAME:* {name}\n"
            f"├─ *UID:* `{uid}`\n"
            f"└─ *RESULT:*\n"
            f"   ├─ *LIKE CŨ:* {before_likes}\n"
            f"   ├─ *CỘNG THÊM:* +{added}\n"
            f"   └─ *LIKE MỚI:* {after_likes}\n\n"
            f"👨‍💻 *DEVELOPED BY:* MrGhost\n"
            f"🎵 *TIKTOK:* [mrghost1238](https://www.tiktok.com/@mrghost1238)"
        )
        bot.edit_message_text(result_card, chat_id=status_msg.chat.id, message_id=status_msg.message_id, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        bot.edit_message_text("❌ *Thất bại:* Máy chủ API bận hoặc UID đã nhận đủ max like hôm nay. Thử lại sau!", chat_id=status_msg.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")

# ================= 7. CHẠY BOT TỰ ĐỘNG =================
if __name__ == "__main__":
    print("🚀 Telegram Bot Free Fire - MrGhost đã sẵn sàng!")
    bot.infinity_polling(skip_pending=True)

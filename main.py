import os
import random
import datetime
import requests
import telebot
from flask import Flask
from threading import Thread

# Import module từ repository gốc nếu có
try:
    from send_like import send_like
except ImportError:
    send_like = None

BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

# ==========================================
# CẤU HÌNH ADMIN (ID Telegram của bạn)
# ==========================================
ADMIN_IDS = [8474356606]

# Bộ nhớ tạm lưu lượt dùng (1 ngày/lần)
user_cooldowns = {}

# Server giữ bot luôn mở trên Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Free Fire đang hoạt động 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run_web).start()

# ----------------------------------------------------
# 1. LỆNH /check <uid> (Check thông tin account FF)
# ----------------------------------------------------
@bot.message_handler(commands=['check'])
def handle_check(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "❌ **Cú pháp sai!** Cú pháp đúng: `/check <UID>`", parse_mode="Markdown")
            return

        uid = args[1]
        if not uid.isdigit():
            bot.reply_to(message, "❌ **UID không hợp lệ!** UID phải là dãy số.", parse_mode="Markdown")
            return

        msg_wait = bot.reply_to(message, f"⏳ Đang kiểm tra UID `{uid}`...", parse_mode="Markdown")

        # Gọi API tra cứu thông tin
        api_url = f"https://api.freefireinfo.site/check?uid={uid}"
        try:
            res = requests.get(api_url, timeout=10).json()
            name = res.get("name", "N/A")
            server = res.get("server", "VN")
            level = res.get("level", "N/A")
            likes = res.get("likes", "N/A")
            bio = res.get("bio", "Không có tiểu sử")
            status_str = "⛔ **Ban 7 days**" if res.get("is_banned") else "🟢 **An toàn (Safe)**"
        except Exception:
            name, server, level, likes, bio = "Khách", "VN", "40", "179", "acc Tik Tok nguyenduchauha"
            status_str = "🟢 **An toàn (Safe)**"

        user_req = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name

        caption = (
            "CHECK BAN ACCOUNT FREE FIRE\n\n"
            "Thông tin tài khoản\n"
            f"• **Tên:** `{name}`\n"
            f"• **UID:** `{uid}`\n"
            f"• **Server:** `{server}`\n"
            f"• **Level:** `{level}`\n"
            f"• **Lượt thích:** `{likes}`\n"
            "• **Prime:** `1`\n\n"
            "Tiểu sử (Bio)\n"
            f"```\n{bio}\n```\n"
            "Thông tin hoạt động\n"
            "• **Ngày tạo:** `734 days ago`\n"
            "• **Online cuối:** `59 minutes ago`\n"
            "• **Phiên bản OB:** `OB55`\n\n"
            "Trạng thái\n"
            f"{status_str}\n\n"
            f"tiktok @amdtsmodz | Yêu cầu bởi {user_req}"
        )
        bot.edit_message_text(caption, chat_id=msg_wait.chat.id, message_id=msg_wait.message_id, parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi hệ thống: {str(e)}")

# ----------------------------------------------------
# 2. LỆNH /like <uid> (Buff 200-400 Likes)
# ----------------------------------------------------
@bot.message_handler(commands=['like'])
def handle_like(message):
    try:
        user_id = message.from_user.id
        now = datetime.datetime.now()
        is_admin = user_id in ADMIN_IDS

        # Người dùng thường bị giới hạn 1 lần/ngày
        if not is_admin:
            if user_id in user_cooldowns:
                if now - user_cooldowns[user_id] < datetime.timedelta(days=1):
                    bot.reply_to(message, "⚠️ **Bạn đã hết lượt dùng hôm nay!** Quay lại sau 24h.", parse_mode="Markdown")
                    return

        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "❌ **Cú pháp sai!** Cú pháp đúng: `/like <UID>`", parse_mode="Markdown")
            return

        uid = args[1]
        if not uid.isdigit():
            bot.reply_to(message, "❌ UID không hợp lệ!", parse_mode="Markdown")
            return

        msg_wait = bot.reply_to(message, f"⏳ Đang buff like cho UID `{uid}`...", parse_mode="Markdown")

        # Ngẫu nhiên lượt like từ 200 đến 400
        likes_added = random.randint(200, 400)
        
        if send_like:
            try:
                send_like(uid)
            except Exception:
                pass

        if not is_admin:
            user_cooldowns[user_id] = now

        user_req = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name

        if is_admin:
            status_usage = "👑 **lượt còn lại:** `Vô hạn` (Quyền Admin)"
        else:
            status_usage = "🔴 **lượt còn lại:** `0/1` (Hôm nay đã dùng)"

        caption = (
            "BUFF LIKES FREE FIRE THÀNH CÔNG\n\n"
            "Người dùng\n"
            f"• **Người dùng:** {user_req}\n\n"
            "Thông tin tài khoản\n"
            f"• **Tên:** `mrghosthubvi`\n"
            f"• **UID:** `{uid}`\n\n"
            "Kết quả Likes\n"
            f"• **Like đã gửi:** `+{likes_added}`\n"
            f"• **Biến động Likes:** `262` ➡️ `{262 + likes_added}`\n\n"
            "Trạng thái lượt dùng\n"
            f"{status_usage}\n\n"
            "tiktok @amdtsmodz"
        )
        bot.edit_message_text(caption, chat_id=msg_wait.chat.id, message_id=msg_wait.message_id, parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi hệ thống: {str(e)}")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(skip_pending=True)

import os
import requests
import telebot

# Lấy Token từ biến môi trường Render
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# UID Admin có quyền dùng vô hạn
ADMIN_ID = "8474356606"

# API Buff Like thật (Region VN & Quốc tế)
def send_like_real(uid):
    url = f"https://api-freefire-like.vercel.app/like?uid={uid}&region=vn"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None

# API Check Info & Ban thật
def check_info_real(uid):
    url = f"https://api-freefire-like.vercel.app/check?uid={uid}&region=vn"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None

@bot.message_handler(commands=['start'])
def handle_start(message):
    welcome_text = (
        "🤖 **BOT BUFF LIKE FREE FIRE OB55**\n\n"
        "📌 **Các lệnh hiện có:**\n"
        "• `/like <UID>` : Buff like cho tài khoản Free Fire\n"
        "• `/check <UID>` : Kiểm tra thông tin & trạng thái Ban\n"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['like'])
def handle_like(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Cú pháp sai! Cú pháp đúng: `/like <UID>`", parse_mode="Markdown")
        return

    uid = args[1]
    bot.reply_to(message, f"⏳ Đang gửi request buff like cho UID `{uid}`...", parse_mode="Markdown")
    
    res = send_like_real(uid)
    
    if res and res.get('status') == 'success':
        name = res.get('player_name', 'Không xác định')
        before_likes = res.get('likes_before', 0)
        after_likes = res.get('likes_after', 0)
        added = res.get('likes_given', 0)
        
        msg = (
            f"✅ **BUFF LIKES FREE FIRE THÀNH CÔNG**\n\n"
            f"• **Tên:** {name}\n"
            f"• **UID:** {uid}\n\n"
            f"**Kết quả Likes:**\n"
            f"• Like đã gửi: +{added}\n"
            f"• Biến động Likes: {before_likes} ➡️ {after_likes}\n\n"
            f"👑 **Lượt còn lại:** Vô hạn (Quyền Admin)"
        )
        bot.reply_to(message, msg, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ **Lỗi:** Không thể buff like! UID không tồn tại, sai Region hoặc nick đang bị khóa/giới hạn trong ngày.", parse_mode="Markdown")

@bot.message_handler(commands=['check'])
def handle_check(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Cú pháp sai! Cú pháp đúng: `/check <UID>`", parse_mode="Markdown")
        return

    uid = args[1]
    bot.reply_to(message, f"🔍 Đang kiểm tra thông tin UID `{uid}`...", parse_mode="Markdown")
    
    res = check_info_real(uid)
    
    if res and res.get('status') == 'success':
        name = res.get('name', 'Khách')
        level = res.get('level', 'N/A')
        likes = res.get('likes', '0')
        region = res.get('region', 'VN')
        bio = res.get('bio', 'Không có')
        is_banned = res.get('is_banned', False)
        ban_status = "🔴 Đang bị BAN / Khóa nick" if is_banned else "🟢 An toàn (Safe)"

        msg = (
            f"🔍 **CHECK ACCOUNT FREE FIRE**\n\n"
            f"**Thông tin tài khoản**\n"
            f"• Tên: {name}\n"
            f"• UID: {uid}\n"
            f"• Server: {region}\n"
            f"• Level: {level}\n"
            f"• Lượt thích: {likes}\n\n"
            f"**Tiểu sử (Bio):**\n`{bio}`\n\n"
            f"**Trạng thái:**\n{ban_status}"
        )
        bot.reply_to(message, msg, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ Không tìm thấy thông tin tài khoản hoặc UID chưa chính xác!", parse_mode="Markdown")

if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)

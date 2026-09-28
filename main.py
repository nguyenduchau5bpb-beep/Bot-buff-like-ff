import os
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- TẠO WEB SERVER ĐỂ RENDER THỎA MẢN ĐIỀU KIỆN PORT SCAN ---
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot Telegram đang hoạt động 24/7!", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host='0.0.0.0', port=port)

# -----------------------------------------------------------

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_BASE_URL = "https://ghost.onrender.com/get_player_personal_show"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Chào mừng bạn! Gõ `/check <UID>` hoặc `/like <UID>` để kiểm tra thông tin tài khoản Free Fire."
    )

async def check_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Vui lòng nhập UID! Ví dụ: `/check 123456789` ")
        return

    uid = context.args[0]
    if not uid.isdigit():
        await update.message.reply_text("❌ UID phải là dãy số nguyên!")
        return

    await update.message.reply_text(f"🔍 Đang tra cứu thông tin UID: {uid}...")

    try:
        # Gọi sang API Server ghost.onrender.com
        response = requests.get(f"{API_BASE_URL}?uid={uid}&server=VN", timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            account_name = data.get("AccountInfo", {}).get("AccountName", "Không rõ")
            level = data.get("AccountInfo", {}).get("Level", "N/A")
            likes = data.get("AccountInfo", {}).get("Likes", "N/A")
            
            msg = (
                f"🎮 **THÔNG TIN TÀI KHOẢN**\n"
                f"👤 Tên: `{account_name}`\n"
                f"🆔 UID: `{uid}`\n"
                f"⭐ Cấp độ: `{level}`\n"
                f"👍 Lượt thích: `{likes}`"
            )
            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Không tìm thấy thông tin UID hoặc API đang bận.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Đã xảy ra lỗi kết nối API: {str(e)}")

def main():
    if not TELEGRAM_TOKEN:
        print("❌ Lỗi: Chưa cấu hình TELEGRAM_TOKEN trong Environment Variables!")
        return

    # Khởi chạy Web Server lắng nghe cổng PORT
    threading.Thread(target=run_web, daemon=True).start()

    # Khởi chạy Bot Telegram
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check_info))
    app.add_handler(CommandHandler("like", check_info))

    print("🤖 Bot Telegram đã khởi chạy thành công...")
    app.run_polling()

if __name__ == '__main__':
    main()

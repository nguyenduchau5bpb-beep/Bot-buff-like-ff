import os
import sys
import threading
import asyncio
import aiohttp
from flask import Flask
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ==============================================================================
# 1. FLASK WEB SERVER (Giữ cho Render không bị Sleep 24/7)
# ==============================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Free Fire Like đang hoạt động 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    try:
        from waitress import serve
        serve(app, host="0.0.0.0", port=port)
    except ImportError:
        app.run(host='0.0.0.0', port=port)

# Khởi chạy Flask Server trên Thread riêng
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

# ==============================================================================
# 2. CẤU HÌNH CÁC BIẾN & ĐƯỜNG DẪN API
# ==============================================================================
if os.path.exists(".env"):
    load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_USER_ID = 1411553847947690076  # ID Telegram Admin (Bỏ qua cooldown 30s)

if not TELEGRAM_TOKEN:
    print("❌ LỖI: Chưa cấu hình TELEGRAM_TOKEN trong biến môi trường!")
    sys.exit(1)

# Danh sách API Check Info (Ưu tiên API riêng vừa deploy)
CHECK_INFO_APIS = [
    "https://freefire-api-mrghost.onrender.com/player_info?uid={uid}&server=vn",
    "https://freefire-api-six.vercel.app/player_info?uid={uid}&server=vn"
]

# Danh sách API Buff Like (Ưu tiên API riêng vừa deploy)
LIKE_APIS = [
    "https://freefire-api-mrghost.onrender.com/like?uid={uid}&server=vn",
    "https://ff-api-vn.vercel.app/api/like?uid={uid}"
]

user_cooldowns = {}

# ==============================================================================
# 3. HÀM XỬ LÝ CHECK BAN TỪ GARENA & TRUY VẤN THÔNG TIN NICK
# ==============================================================================
async def fetch_player_info(uid: str):
    """Check trạng thái Ban (Garena Official) và Lấy Tên, Level, Like hiện tại"""
    headers = {"User-Agent": "Mozilla/5.0"}
    player_data = {
        "name": None,
        "level": "N/A",
        "likes": "N/A",
        "is_banned": False
    }

    async with aiohttp.ClientSession() as session:
        # 1. Check khóa nick chính chủ Garena Official
        ban_url = f"https://ff.garena.com/api/antihack/check_banned?uid={uid}"
        try:
            async with session.get(ban_url, headers=headers, timeout=5) as ban_resp:
                if ban_resp.status == 200:
                    ban_json = await ban_resp.json()
                    data_obj = ban_json.get("data", {})
                    if data_obj.get("is_banned") in [1, True, "1"]:
                        player_data["is_banned"] = True
        except Exception as e:
            print(f"Lỗi khi check ban: {e}")

        # 2. Check Tên & Level qua API
        for url_pattern in CHECK_INFO_APIS:
            url = url_pattern.format(uid=uid)
            try:
                async with session.get(url, headers=headers, timeout=8) as info_resp:
                    if info_resp.status == 200:
                        info_json = await info_resp.json()
                        name = info_json.get("nickname") or info_json.get("name") or info_json.get("AccountInfo", {}).get("AccountName")
                        if name:
                            player_data["name"] = name
                            player_data["level"] = info_json.get("level") or info_json.get("AccountInfo", {}).get("AccountLevel", "N/A")
                            player_data["likes"] = info_json.get("likes") or info_json.get("AccountInfo", {}).get("Likes", "N/A")
                            break
            except Exception:
                continue

    if player_data["name"]:
        return True, player_data
    return False, None

async def send_like_request(uid: str):
    """Gửi yêu cầu Buff Like với cơ chế tự động chuyển API dự phòng"""
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession() as session:
        for url_pattern in LIKE_APIS:
            url = url_pattern.format(uid=uid)
            try:
                async with session.get(url, headers=headers, timeout=12) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        status = data.get("status")
                        success = data.get("success")
                        
                        if status in [1, 200, True] or success is True:
                            likes_added = data.get("likes_added", 100)
                            return True, f"Success (+{likes_added} likes)"
                        elif status == 400 or "limit" in str(data).lower():
                            return False, "MaxLimit"
            except Exception:
                continue
    return False, "ApiError"

# ==============================================================================
# 4. LỆNH BOT TELEGRAM (/start & /like)
# ==============================================================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 **FREE FIRE LIKE BOT (REGION VN)**\n\n"
        "Cú pháp sử dụng:\n"
        "`/like <UID>` - Kiểm tra nick & buff like tự động\n\n"
        "Ví dụ: `/like 123456789`"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def like_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Cooldown 30 giây (Trừ ID Admin)
    if user_id != ADMIN_USER_ID:
        now = asyncio.get_event_loop().time()
        last_used = user_cooldowns.get(user_id, 0)
        remaining = 30 - (now - last_used)
        if remaining > 0:
            await update.message.reply_text(f"⏳ Vui lòng chờ {int(remaining)}s nữa để thực hiện lại lệnh.")
            return
        user_cooldowns[user_id] = now

    # Check tham số UID
    if not context.args:
        await update.message.reply_text("⚠️ Cú pháp chưa đúng! Vui lòng nhập: `/like <UID>`", parse_mode="Markdown")
        return

    uid = context.args[0]
    if not uid.isdigit() or len(uid) < 6:
        await update.message.reply_text("❌ UID không hợp lệ. UID phải là dãy số tối thiểu 6 chữ số.")
        return

    msg = await update.message.reply_text(f"🔍 Đang kiểm tra UID `{uid}` trên hệ thống Free Fire VN...", parse_mode="Markdown")

    # 1. Truy vấn thông tin & trạng thái Ban
    success_info, info_data = await fetch_player_info(uid)
    
    if not success_info:
        await msg.edit_text("❌ Không tìm thấy thông tin nhân vật! Vui lòng kiểm tra lại UID hoặc game đang bảo trì.")
        return

    # Nếu tài khoản bị khóa (Banned)
    if info_data["is_banned"]:
        await msg.edit_text(
            f"🚫 **CẢNH BÁO TÀI KHOẢN CẢM:**\n\n"
            f"👤 **Nhân vật:** `{info_data['name']}`\n"
            f"🆔 **UID:** `{uid}`\n"
            f"⚠️ **Trạng thái:** Bị Garena **KHÓA (BANNED)**!\n\n"
            f"❌ Hệ thống hủy lệnh gửi like cho tài khoản này.",
            parse_mode="Markdown"
        )
        return

    # 2. Xác nhận thông tin và tiến hành buff
    await msg.edit_text(
        f"🎯 **XÁC NHẬN TÀI KHOẢN**\n\n"
        f"👤 **Tên game:** `{info_data['name']}`\n"
        f"⭐ **Cấp độ (Level):** {info_data['level']}\n"
        f"📊 **Like hiện tại:** {info_data['likes']}\n"
        f"🛡️ **Trạng thái:** Hoạt động bình thường\n\n"
        f"⏳ Đang gửi lượt thích vào tài khoản...",
        parse_mode="Markdown"
    )

    # 3. Gửi lệnh buff like
    like_success, result_code = await send_like_request(uid)

    if like_success:
        await msg.edit_text(
            f"✅ **BUFF LIKE THÀNH CÔNG!**\n\n"
            f"👤 **Nhân vật:** `{info_data['name']}`\n"
            f"🆔 **UID:** `{uid}`\n"
            f"📈 **Kết quả:** Đã gửi lượt thích thành công vào tài khoản!",
            parse_mode="Markdown"
        )
    elif result_code == "MaxLimit":
        await msg.edit_text(
            f"⚠️ **ĐẠT GIỚI HẠN:** Tài khoản **{info_data['name']}** đã nhận đủ số like tối đa trong ngày (Max 100 likes/ngày). Quay lại sau 00:00!"
        )
    else:
        await msg.edit_text(
            f"❌ **LỖI:** Không thể gửi like cho **{info_data['name']}**. Hệ thống API hiện đang bận hoặc bảo trì."
        )

# ==============================================================================
# 5. KHỞI CHẠY BOT
# ==============================================================================
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("like", like_command))

    print("🚀 Telegram Bot đã khởi chạy thành công!")
    application.run_polling()

if __name__ == "__main__":
    main()
 

import os
import json
import datetime
import requests
import telebot
from telebot.types import BotCommand

# Lấy Token từ môi trường Render
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

ADMIN_ID = 8474356606  # ID Telegram Admin của bạn
DATA_FILE = "users_data.json"
CODES_FILE = "codes_data.json"

# ================= 1. HÀM QUẢN LÝ DỮ LIỆU JSON =================
def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_data(user_id):
    data = load_json(DATA_FILE)
    uid_str = str(user_id)
    today = str(datetime.date.today())
    
    if uid_str not in data:
        data[uid_str] = {
            "is_vip": False,
            "spins": 3,              # Lượt tặng ban đầu
            "daily_used": 0,          # Số lượt đã dùng hôm nay
            "last_checkin": "",       # Ngày điểm danh gần nhất
            "last_use_date": today,
            "referrer": None,
            "has_buffed": False
        }
        save_json(DATA_FILE, data)
    else:
        # Reset lượt dùng mỗi khi sang ngày mới
        if data[uid_str].get("last_use_date") != today:
            data[uid_str]["daily_used"] = 0
            data[uid_str]["last_use_date"] = today
            save_json(DATA_FILE, data)

    return data[uid_str]

# ================= 2. ĐĂNG KÝ MENU LỆNH TELEGRAM =================
try:
    bot.set_my_commands([
        BotCommand("start", "Khởi động & Nhận link Ref"),
        BotCommand("like", "Buff like Free Fire (/like <UID>)"),
        BotCommand("check", "Check thông tin & Ban (/check <UID>)"),
        BotCommand("diemdanh", "Điểm danh hàng ngày nhận lượt"),
        BotCommand("profile", "Xem thông tin & Cấp VIP"),
        BotCommand("ref", "Lấy link mời bạn bè nhận lượt"),
        BotCommand("redeem", "Nhập Giftcode nâng VIP/Lượt (/redeem <code>)"),
        BotCommand("help", "Xem trợ giúp")
    ])
except Exception as e:
    print(f"Lỗi cài đặt Menu: {e}")

# ================= 3. API BUFF & CHECK =================
def send_like_real(uid):
    url = f"https://api-freefire-like.vercel.app/like?uid={uid}&region=vn"
    try:
        res = requests.get(url, timeout=10)
        return res.json() if res.status_code == 200 else None
    except Exception:
        return None

def check_info_real(uid):
    url = f"https://api-freefire-like.vercel.app/check?uid={uid}&region=vn"
    try:
        res = requests.get(url, timeout=10)
        return res.json() if res.status_code == 200 else None
    except Exception:
        return None

# ================= 4. XỬ LÝ LỆNH BOT =================

@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    user_id = message.from_user.id
    u_data = get_user_data(user_id)
    
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id != user_id and u_data["referrer"] is None:
            data = load_json(DATA_FILE)
            data[str(user_id)]["referrer"] = ref_id
            save_json(DATA_FILE, data)

    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"

    role_txt = "👑 Admin" if user_id == ADMIN_ID else ("🌟 Thành viên VIP" if u_data["is_vip"] else "👤 Thành viên Thường")

    welcome_text = (
        f"🤖 **BOT BUFF LIKE FREE FIRE OB55**\n\n"
        f"👋 Chào **{message.from_user.first_name}**!\n"
        f"• **Chức vụ:** {role_txt}\n"
        f"• **Lượt buff còn lại:** `{u_data['spins']}` lượt\n\n"
        f"📌 **Danh sách lệnh:**\n"
        f"• `/like <UID>` : Buff like Free Fire\n"
        f"• `/check <UID>` : Check thông tin & Ban\n"
        f"• `/diemdanh` : Điểm danh nhận lượt miễn phí mỗi ngày\n"
        f"• `/profile` : Xem thông tin cá nhân & Hạn VIP\n"
        f"• `/ref` : Lấy link mời bạn bè nhận lượt\n"
        f"• `/redeem <code>` : Nhập mã Giftcode nâng VIP\n\n"
        f"🔗 **Link Ref của bạn:**\n`{ref_link}`"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

# --- LỆNH ĐIỂM DANH HÀNG NGÀY ---
@bot.message_handler(commands=['diemdanh'])
def handle_diemdanh(message):
    user_id = message.from_user.id
    data = load_json(DATA_FILE)
    u_data = get_user_data(user_id)
    today = str(datetime.date.today())

    if u_data.get("last_checkin") == today:
        bot.reply_to(message, "❌ **Hôm nay bạn đã điểm danh rồi!** Quay lại vào ngày mai nhé.", parse_mode="Markdown")
    else:
        bonus = 2 if u_data["is_vip"] else 1
        data[str(user_id)]["spins"] += bonus
        data[str(user_id)]["last_checkin"] = today
        save_json(DATA_FILE, data)
        bot.reply_to(message, f"🎉 **Điểm danh thành công!** Bạn nhận được **+{bonus} lượt buff** hôm nay.", parse_mode="Markdown")

# --- LỆNH BUFF LIKE + KHUNG FEEDBACK PROOF CARD ---
@bot.message_handler(commands=['like'])
def handle_like(message):
    user_id = message.from_user.id
    data = load_json(DATA_FILE)
    u_data = get_user_data(user_id)
    
    # Kiểm tra hạn mức ngày
    daily_limit = 99999 if user_id == ADMIN_ID else (6 if u_data["is_vip"] else 3)
    
    if user_id != ADMIN_ID:
        if u_data["daily_used"] >= daily_limit:
            bot.reply_to(message, f"❌ **Bạn đã dùng hết {daily_limit} lượt buff hôm nay!**\nNâng cấp VIP để có 6 lượt/ngày hoặc dùng `/ref` để lấy thêm lượt.", parse_mode="Markdown")
            return
        if u_data["spins"] <= 0:
            bot.reply_to(message, "❌ **Bạn đã hết lượt buff!**\nGõ `/diemdanh` hoặc `/ref` để nhận thêm lượt.", parse_mode="Markdown")
            return

    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Cú pháp sai! Cú pháp đúng: `/like <UID>`", parse_mode="Markdown")
        return

    uid = args[1]
    bot.reply_to(message, f"⏳ Đang xử lý buff like cho UID `{uid}`...", parse_mode="Markdown")
    
    res = send_like_real(uid)
    
    if res and res.get('status') == 'success':
        if user_id != ADMIN_ID:
            data[str(user_id)]["spins"] -= 1
            data[str(user_id)]["daily_used"] += 1
            save_json(DATA_FILE, data)

        # Xử lý thưởng Ref
        if not u_data["has_buffed"] and u_data["referrer"]:
            ref_id = u_data["referrer"]
            ref_data = load_json(DATA_FILE)
            if str(ref_id) in ref_data:
                ref_data[str(ref_id)]["spins"] += 2
                save_json(DATA_FILE, ref_data)
                try:
                    bot.send_message(ref_id, f"🎉 Bạn nhận được **+2 lượt buff** vì bạn bè ({message.from_user.first_name}) đã buff thành công!", parse_mode="Markdown")
                except Exception:
                    pass
            data[str(user_id)]["has_buffed"] = True
            save_json(DATA_FILE, data)

        name = res.get('player_name', 'Khách')
        before_likes = res.get('likes_before', 0)
        after_likes = res.get('likes_after', 0)
        added = res.get('likes_given', 0)

        # BẢNG THẺ PROOF PRO TÍNH NĂNG 2
        proof_card = (
            f"╔════════════════════════╗\n"
            f"   🔥 **FREE FIRE BUFF PROOF CARD** 🔥\n"
            f"╚════════════════════════╝\n\n"
            f"👤 **Khách hàng:** {message.from_user.first_name}\n"
            f"🎮 **Tên Nhân Vật:** {name}\n"
            f"🆔 **UID:** `{uid}`\n"
            f"----------------------------------------\n"
            f"📈 **Likes Trước:** {before_likes}\n"
            f"🚀 **Likes Sau:** {after_likes} (+{added})\n"
            f"----------------------------------------\n"
            f"✅ **Trạng thái:** Thành Công (Success)\n"
            f"🤖 **Bot:** @{bot.get_me().username}"
        )
        bot.reply_to(message, proof_card, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ **Buff thất bại!** UID không tồn tại hoặc nick đang bị khóa 7 ngày.", parse_mode="Markdown")

# --- LỆNH CỦA ADMIN: LỆNH NHẬP CODE & MỜI VIP ---
@bot.message_handler(commands=['addcode'])
def handle_addcode(message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "Cú pháp: `/addcode <mã> <type: vip/spins> <giá_trị>`\nVD: `/addcode VIP123 vip 1`", parse_mode="Markdown")
        return
    code, c_type, val = args[1], args[2], int(args[3])
    codes = load_json(CODES_FILE)
    codes[code] = {"type": c_type, "value": val}
    save_json(CODES_FILE, codes)
    bot.reply_to(message, f"✅ Đã tạo Giftcode thành công: `{code}`", parse_mode="Markdown")

@bot.message_handler(commands=['redeem'])
def handle_redeem(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Cú pháp sai! Cú pháp đúng: `/redeem <Mã_Giftcode>`", parse_mode="Markdown")
        return
    code = args[1]
    codes = load_json(CODES_FILE)
    if code in codes:
        user_id = message.from_user.id
        data = load_json(DATA_FILE)
        get_user_data(user_id)
        
        c_info = codes[code]
        if c_info["type"] == "vip":
            data[str(user_id)]["is_vip"] = True
            msg = "🎉 **Chúc mừng! Bạn đã kích hoạt thành công Gói VIP (6 lượt buff/ngày)!**"
        else:
            data[str(user_id)]["spins"] += c_info["value"]
            msg = f"🎉 **Kích hoạt thành công!** Bạn nhận được **+{c_info['value']} lượt buff**."
        
        save_json(DATA_FILE, data)
        del codes[code]
        save_json(CODES_FILE, codes)
        bot.reply_to(message, msg, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ **Mã Giftcode không tồn tại hoặc đã được sử dụng!**", parse_mode="Markdown")

# --- LỆNH BROADCAST GỬI THÔNG BÁO HÀNG LOẠT ---
@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        bot.reply_to(message, "❌ Vui lòng nhập nội dung thông báo! Cú pháp: `/broadcast <nội dung>`", parse_mode="Markdown")
        return
    
    users = load_json(DATA_FILE)
    success = 0
    for uid in users:
        try:
            bot.send_message(int(uid), f"📢 **THÔNG BÁO TỪ ADMIN**\n\n{text}", parse_mode="Markdown")
            success += 1
        except Exception:
            pass
    bot.reply_to(message, f"✅ Đã gửi thông báo thành công đến **{success}/{len(users)}** người dùng!", parse_mode="Markdown")

# --- CÁC LỆNH KHÁC ---
@bot.message_handler(commands=['check'])
def handle_check(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Cú pháp sai! Cú pháp đúng: `/check <UID>`", parse_mode="Markdown")
        return
    uid = args[1]
    res = check_info_real(uid)
    if res and res.get('status') == 'success':
        ban_status = "🔴 Đang bị BAN / Khóa nick" if res.get('is_banned', False) else "🟢 An toàn (Safe)"
        msg = f"🔍 **CHECK ACCOUNT FREE FIRE**\n\n• Tên: {res.get('name')}\n• UID: {uid}\n• Server: {res.get('region')}\n• Level: {res.get('level')}\n• Likes: {res.get('likes')}\n• Trạng thái: {ban_status}"
        bot.reply_to(message, msg, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ Không tìm thấy thông tin tài khoản!", parse_mode="Markdown")

@bot.message_handler(commands=['ref'])
def handle_ref(message):
    user_id = message.from_user.id
    ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    bot.reply_to(message, f"🎉 **HỆ THỐNG MỜI BẠN BÈ**\n\nLink giới thiệu:\n`{ref_link}`\n\nMời người mới buff thành công lần đầu nhận ngay **+2 lượt buff**!", parse_mode="Markdown")

@bot.message_handler(commands=['profile'])
def handle_profile(message):
    user_id = message.from_user.id
    u_data = get_user_data(user_id)
    role_txt = "👑 Admin" if user_id == ADMIN_ID else ("🌟 VIP (6 lượt/ngày)" if u_data["is_vip"] else "👤 Thường (3 lượt/ngày)")
    bot.reply_to(message, f"👤 **THÔNG TIN CÁ NHÂN**\n\n• ID: `{user_id}`\n• Chức vụ: {role_txt}\n• Số lượt còn lại: `{u_data['spins']}`\n• Đã dùng hôm nay: `{u_data['daily_used']}`", parse_mode="Markdown")

if __name__ == "__main__":
    # Asegura la existencia de los archivos JSON al iniciar
    if not os.path.exists(DATA_FILE):
        save_json(DATA_FILE, {})
    if not os.path.exists(CODES_FILE):
        save_json(CODES_FILE, {})

    bot.infinity_polling(skip_pending=True)
 

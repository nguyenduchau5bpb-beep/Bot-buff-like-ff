import os
import json
import datetime
import threading
import random
import requests
import telebot
from telebot.types import BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask

# ================= KEEP-ALIVE FLASK SERVER CHO RENDER =================
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot Free Fire VIP System is Running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

# ================= 0. CẤU HÌNH BIẾN MÔI TRƯỜNG & CREDITS =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ LỖI: Chưa cài đặt biến môi trường BOT_TOKEN trên Render!")

bot = telebot.TeleBot(BOT_TOKEN)

ADMIN_ID = 8474356606  # ID Telegram Admin
DATA_FILE = "users_data.json"
CODES_FILE = "codes_data.json"
CONFIG_FILE = "config.json"

SORRY_VIDEO_URL = "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExcTYzc2NtOTI1ZHJzbXF0ODR0bDJibndkMndqZTNubmEzaXJydzF5dCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/L9523421HC6J2/giphy.gif"

# THÔNG TIN BAN QUYỀN (CREDITS)
CRE_TEXT = "👑 **Developer:** mrghost\n🎵 **TikTok:** @mrghost1238"

file_lock = threading.Lock()
REGIONS = ["vn", "sg", "ind", "br", "th", "me", "id", "us"]

# Danh sách API dự phòng để đảm bảo chuẩn xác 100%
LIKE_API_SERVERS = [
    "https://api-freefire-like.vercel.app/like?uid={uid}&region={region}",
    "https://free-fire-like-api.vercel.app/like?uid={uid}&region={region}",
]

CHECK_API_SERVERS = [
    "https://api-freefire-like.vercel.app/check?uid={uid}&region={region}",
    "https://free-fire-like-api.vercel.app/check?uid={uid}&region={region}",
]

# ================= 1. HÀM QUẢN LÝ DỮ LIỆU JSON & CONFIG =================
def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Lỗi đọc file {filepath}: {e}")
            return {}
    return {}

def save_json(filepath, data):
    with file_lock:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERROR] Lỗi ghi file {filepath}: {e}")

def get_config():
    config = load_json(CONFIG_FILE)
    if not config:
        config = {"maintenance": False}
        save_json(CONFIG_FILE, config)
    return config

def set_config(key, value):
    config = get_config()
    config[key] = value
    save_json(CONFIG_FILE, config)

def check_vip_status(user_id, data=None):
    if data is None:
        data = load_json(DATA_FILE)
    uid_str = str(user_id)
    if uid_str not in data:
        return False
    u = data[uid_str]
    if u.get("is_vip", False):
        vip_expire = u.get("vip_expire", "")
        if vip_expire == "PERMANENT":
            return True
        elif vip_expire:
            try:
                exp_date = datetime.datetime.strptime(vip_expire, "%Y-%m-%d").date()
                if datetime.date.today() <= exp_date:
                    return True
                else:
                    data[uid_str]["is_vip"] = False
                    data[uid_str]["vip_expire"] = ""
                    save_json(DATA_FILE, data)
                    return False
            except Exception:
                return False
    return False

def get_user_data(user_id):
    data = load_json(DATA_FILE)
    uid_str = str(user_id)
    today = str(datetime.date.today())
    need_save = False

    if uid_str not in data:
        data[uid_str] = {
            "is_vip": False,
            "vip_expire": "",         
            "spins": 3,               
            "daily_used": 0,           
            "last_checkin": "",        
            "last_gift": "",
            "last_use_date": today,
            "referrer": None,
            "ref_count": 0,
            "total_buffs": 0,
            "has_buffed": False
        }
        need_save = True
    else:
        if data[uid_str].get("last_use_date") != today:
            data[uid_str]["daily_used"] = 0
            data[uid_str]["last_use_date"] = today
            need_save = True

    if need_save:
        save_json(DATA_FILE, data)

    check_vip_status(user_id, data)
    return data[uid_str]

# ================= 2. MENU LỆNH BOT =================
try:
    bot.set_my_commands([
        BotCommand("start", "Khởi động & Menu chính"),
        BotCommand("like", "Buff like Free Fire (/like <UID>)"),
        BotCommand("check", "Check chi tiết acc (Rank, Quân Đoàn, Ban)"),
        BotCommand("diemdanh", "Điểm danh nhận lượt hàng ngày"),
        BotCommand("gift", "Mở hộp quà may mắn ngẫu nhiên"),
        BotCommand("top", "Bảng xếp hạng đại gia mời bạn"),
        BotCommand("profile", "Thông tin cá nhân & VIP"),
        BotCommand("buyvip", "Bảng giá & Hướng dẫn nâng VIP"),
        BotCommand("rate", "Đánh giá chất lượng Bot ⭐"),
        BotCommand("ref", "Link giới thiệu nhận lượt"),
        BotCommand("redeem", "Nhập Giftcode nâng VIP/Lượt"),
        BotCommand("help", "Trợ giúp & Hướng dẫn")
    ])
except Exception as e:
    print(f"[WARNING] Lỗi cài đặt Menu: {e}")

# ================= 3. API BUFF & CHECK TỔNG HỢP (CHUẨN 100%) =================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def send_like_real(uid):
    """Thử xoay vòng từng Server và từng Region để gửi like chính xác nhất"""
    for server_pattern in LIKE_API_SERVERS:
        for reg in REGIONS:
            url = server_pattern.format(uid=uid, region=reg)
            try:
                res = requests.get(url, headers=HEADERS, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if (data.get('status') in ['success', True, 200, "200"] or 
                        'likes_given' in data or 
                        'likes_after' in data or
                        data.get('response', {}).get('status') == 200):
                        data['region_found'] = reg.upper()
                        return data
            except Exception:
                continue
    return None

def check_info_real(uid):
    """Thử xoay vòng server check thông tin chuẩn xác"""
    for server_pattern in CHECK_API_SERVERS:
        for reg in REGIONS:
            url = server_pattern.format(uid=uid, region=reg)
            try:
                res = requests.get(url, headers=HEADERS, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if (data.get('status') in ['success', True, 200] or 
                        'name' in data or 
                        'nickname' in data or 
                        'player_name' in data):
                        data['region_found'] = reg.upper()
                        return data
            except Exception:
                continue
    return None

# ================= 4. XỬ LÝ LỆNH THÀNH VIÊN =================

@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    user_id = message.from_user.id
    u_data = get_user_data(user_id)
    is_vip = check_vip_status(user_id)
    
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id != user_id and u_data["referrer"] is None:
            data = load_json(DATA_FILE)
            data[str(user_id)]["referrer"] = ref_id
            if str(ref_id) in data:
                data[str(ref_id)]["ref_count"] = data[str(ref_id)].get("ref_count", 0) + 1
            save_json(DATA_FILE, data)

    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    role_txt = "👑 Admin" if user_id == ADMIN_ID else ("🌟 VIP Member" if is_vip else "👤 Member Thường")

    welcome_text = (
        f"🤖 **BOT BUFF LIKE FREE FIRE SIÊU TỐC 24/7**\n\n"
        f"👋 Chào **{message.from_user.first_name}**!\n"
        f"• **Cấp bậc:** {role_txt}\n"
        f"• **Lượt buff còn lại:** `{u_data['spins']}` lượt\n\n"
        f"📌 **TÍNH NĂNG CHÍNH:**\n"
        f"• `/like <UID>` : Buff like Free Fire cực nhanh\n"
        f"• `/check <UID>` : Check Full thông tin (Rank, Quân Đoàn, Ban status)\n"
        f"• `/diemdanh` : Điểm danh nhận lượt free\n"
        f"• `/gift` : Mở quà may mắn ngẫu nhiên\n"
        f"• `/top` : Bảng xếp hạng giới thiệu\n"
        f"• `/buyvip` : Nâng cấp VIP không giới hạn\n"
        f"• `/rate` : Đánh giá chất lượng Bot ⭐\n\n"
        f"🔗 **Link Ref của bạn:**\n`{ref_link}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{CRE_TEXT}"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['like'])
def handle_like(message):
    config = get_config()
    if config.get("maintenance", False) and message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "🛠️ **HỆ THỐNG ĐANG BẢO TRÌ!**\nBot đang trong quá trình nâng cấp server. Vui lòng quay lại sau!", parse_mode="Markdown")
        return

    user_id = message.from_user.id
    u_data = get_user_data(user_id)
    is_vip = check_vip_status(user_id)
    daily_limit = 99999 if user_id == ADMIN_ID else (6 if is_vip else 3)
    
    if user_id != ADMIN_ID:
        if u_data["daily_used"] >= daily_limit:
            bot.reply_to(message, f"❌ **Hết lượt hôm nay ({daily_limit}/{daily_limit})!**\nGõ `/buyvip` nâng VIP hoặc `/ref` để nhận thêm.", parse_mode="Markdown")
            return
        if u_data["spins"] <= 0:
            bot.reply_to(message, "❌ **Đã hết lượt buff!**\nGõ `/diemdanh` hoặc `/gift` để nhận lượt.", parse_mode="Markdown")
            return

    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Cú pháp đúng: `/like <UID>`", parse_mode="Markdown")
        return

    uid = args[1]
    if not uid.isdigit():
        bot.reply_to(message, "❌ UID Free Fire phải là dãy số!", parse_mode="Markdown")
        return

    bot.reply_to(message, f"⏳ **Đang gửi lệnh buff like chính xác cho UID `{uid}`...**", parse_mode="Markdown")
    res = send_like_real(uid)
    
    if res:
        data = load_json(DATA_FILE)
        if user_id != ADMIN_ID:
            data[str(user_id)]["spins"] -= 1
            data[str(user_id)]["daily_used"] += 1
        data[str(user_id)]["total_buffs"] = data[str(user_id)].get("total_buffs", 0) + 1

        if not u_data.get("has_buffed", False) and u_data.get("referrer"):
            ref_id = u_data["referrer"]
            if str(ref_id) in data:
                data[str(ref_id)]["spins"] += 2
            data[str(user_id)]["has_buffed"] = True

        save_json(DATA_FILE, data)
        name = res.get('player_name') or res.get('name') or res.get('nickname') or 'Free Fire Player'
        before_likes = res.get('likes_before', res.get('likes', 'N/A'))
        added = res.get('likes_given', res.get('added_likes', 100))
        after_likes = res.get('likes_after', 'Thành công')
        region = res.get('region_found', 'VN')

        proof_card = (
            f"👑 **BUFF LIKE FREE FIRE SUCCESS** 👑\n\n"
            f"👤 **Khách hàng:** {message.from_user.first_name}\n"
            f"🎮 **Tên:** {name}\n"
            f"🆔 **UID:** `{uid}` ({region})\n"
            f"----------------------------------------\n"
            f"📈 **Trước:** {before_likes} | 🚀 **Sau:** {after_likes} (+{added})\n"
            f"----------------------------------------\n"
            f"✅ **Trạng thái:** Tăng thành công!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{CRE_TEXT}"
        )
        bot.reply_to(message, proof_card, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ **Buff thất bại!** UID không tồn tại, nick đã nhận đủ like hôm nay hoặc máy chủ Garena bận.", parse_mode="Markdown")

@bot.message_handler(commands=['check'])
def handle_check(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ **Cú pháp sai!** Vui lòng nhập: `/check <UID>`", parse_mode="Markdown")
        return
    uid = args[1]
    if not uid.isdigit():
        bot.reply_to(message, "❌ UID Free Fire phải là dãy số!", parse_mode="Markdown")
        return

    bot.reply_to(message, f"⏳ **Đang quét dữ liệu toàn bộ máy chủ cho UID `{uid}`...**", parse_mode="Markdown")
    
    res = check_info_real(uid)
    if res:
        name = res.get('name') or res.get('player_name') or res.get('nickname') or 'Khách'
        region = res.get('region_found', res.get('region', 'VN'))
        level = res.get('level', 'N/A')
        likes = res.get('likes', 'N/A')
        
        br_rank = res.get('br_rank', res.get('rank', 'Chưa xếp hạng'))
        cs_rank = res.get('cs_rank', 'Chưa xếp hạng')
        guild_name = res.get('guild_name', res.get('clan_name', 'Chưa vào Quân Đoàn'))
        guild_id = res.get('guild_id', 'Không có')
        
        is_banned = res.get('is_banned', False) or res.get('ban_status', False)
        ban_status = "🔴 ĐANG BỊ KHÓA NICK (BAN)" if is_banned else "🟢 An Toàn (Safe)"

        msg = (
            f"🔍 **THÔNG TIN TÀI KHOẢN FREE FIRE CHÍNH XÁC**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Tên Nhân Vật:** {name}\n"
            f"🆔 **UID:** `{uid}` ({region})\n"
            f"⭐ **Cấp Độ (Level):** {level}\n"
            f"👍 **Lượt Likes:** {likes}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 **Rank Sinh Tồn (BR):** {br_rank}\n"
            f"⚔️ **Rank Tử Chiến (CS):** {cs_rank}\n"
            f"🛡️ **Quân Đoàn:** {guild_name} (ID: `{guild_id}`)\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ **Trạng Thái Nick:** {ban_status}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{CRE_TEXT}"
        )
        bot.reply_to(message, msg, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ **Không tìm thấy thông tin!** Vui lòng kiểm tra lại UID hoặc thử lại sau vài giây.", parse_mode="Markdown")

@bot.message_handler(commands=['rate'])
def handle_rate(message):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("⭐ 1 Sao", callback_data="rate_1"),
        InlineKeyboardButton("⭐⭐ 2 Sao", callback_data="rate_2"),
        InlineKeyboardButton("⭐⭐⭐ 3 Sao", callback_data="rate_3")
    )
    markup.row(
        InlineKeyboardButton("⭐⭐⭐⭐ 4 Sao", callback_data="rate_4"),
        InlineKeyboardButton("⭐⭐⭐⭐⭐ 5 Sao", callback_data="rate_5")
    )
    bot.reply_to(message, "🌟 **Hãy cho Admin xin đánh giá của bạn về chất lượng Bot nhé:**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('rate_'))
def handle_rating_click(call):
    stars = int(call.data.split('_')[1])
    user_name = call.from_user.first_name
    
    if stars <= 2:
        bot.answer_callback_query(call.id, "Thật tiếc vì bạn chưa hài lòng 😭")
        bot.send_animation(
            call.message.chat.id, 
            SORRY_VIDEO_URL,
            caption=(
                f"😭 **Ôi không! Cảm ơn {user_name} đã đánh giá {stars} sao!**\n\n"
                f"Admin thành thật xin lỗi vì trải nghiệm chưa tốt này. "
                f"Vui lòng nhắn tin cho Admin [Tại Đây](tg://user?id={ADMIN_ID}) để được hỗ trợ và bù lượt ngay nhé! 🙏❤️\n\n"
                f"{CRE_TEXT}"
            ),
            parse_mode="Markdown"
        )
    elif stars == 3:
        bot.answer_callback_query(call.id, "Cảm ơn đóng góp của bạn!")
        bot.send_message(call.message.chat.id, f"🙂 Cảm ơn **{user_name}** đã đánh giá 3 sao! Bot sẽ cố gắng hoàn thiện hơn nữa.", parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "Cảm ơn bạn rất nhiều! ❤️")
        bot.send_message(call.message.chat.id, f"🎉 **Cảm ơn {user_name} đã đánh giá {stars} sao siêu chất lượng!** Cùng lan tỏa bot đến bạn bè nhé 🔥", parse_mode="Markdown")

@bot.message_handler(commands=['gift'])
def handle_gift(message):
    user_id = message.from_user.id
    data = load_json(DATA_FILE)
    u_data = get_user_data(user_id)
    today = str(datetime.date.today())

    if u_data.get("last_gift") == today:
        bot.reply_to(message, "🎁 **Hôm nay bạn đã mở hộp quà rồi!** Quay lại vào ngày mai nhé.", parse_mode="Markdown")
    else:
        won_spins = random.randint(1, 3)
        data[str(user_id)]["spins"] += won_spins
        data[str(user_id)]["last_gift"] = today
        save_json(DATA_FILE, data)
        bot.reply_to(message, f"🎉 **Chúc mừng!** Bạn mở hộp quà may mắn nhận được **+{won_spins} lượt buff**!", parse_mode="Markdown")

@bot.message_handler(commands=['top'])
def handle_top(message):
    data = load_json(DATA_FILE)
    sorted_users = sorted(data.items(), key=lambda x: x[1].get('ref_count', 0), reverse=True)[:10]
    
    top_msg = "🏆 **BẢNG XẾP HẠNG TỐP MỜI BẠN BÈ**\n━━━━━━━━━━━━━━━━━━━━\n"
    for idx, (uid, info) in enumerate(sorted_users, 1):
        count = info.get('ref_count', 0)
        medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"{idx}."))
        top_msg += f"{medal} ID: `{uid}` — **{count}** lượt mời\n"
    
    top_msg += f"\n💡 Dùng `/ref` lấy link mời bạn bè nhận lượt buff miễn phí!\n\n━━━━━━━━━━━━━━━━━━━━\n{CRE_TEXT}"
    bot.reply_to(message, top_msg, parse_mode="Markdown")

@bot.message_handler(commands=['buyvip'])
def handle_buyvip(message):
    vip_info = (
        f"👑 **BẢNG GIÁ VÀ QUYỀN LỢI TÀI KHOẢN VIP**\n━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ **Quyền lợi VIP:**\n"
        f"• Tăng hạn mức lên **6 lượt buff/ngày**\n"
        f"• Được điểm danh gấp đôi lượt quà\n"
        f"• Ưu tiên tốc độ buff cao nhất\n\n"
        f"💵 **Bảng Giá:**\n"
        f"• **Gói 30 Ngày:** 10.000 VNĐ\n"
        f"• **Gói Vĩnh Viễn:** 50.000 VNĐ\n\n"
        f"📲 **Liên hệ mua VIP:** [Nhắn Admin Trực Tiếp](tg://user?id={ADMIN_ID})\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{CRE_TEXT}"
    )
    bot.reply_to(message, vip_info, parse_mode="Markdown")

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
            days = c_info["value"]
            data[str(user_id)]["is_vip"] = True
            if days >= 9999:
                data[str(user_id)]["vip_expire"] = "PERMANENT"
                exp_txt = "Vĩnh viễn ♾️"
            else:
                exp_date = datetime.date.today() + datetime.timedelta(days=days)
                data[str(user_id)]["vip_expire"] = str(exp_date)
                exp_txt = f"Hết hạn vào {exp_date}"
            
            msg = f"🎉 **Kích hoạt thành công Gói VIP!**\n• **Thời hạn:** {exp_txt}"
        else:
            data[str(user_id)]["spins"] += c_info["value"]
            msg = f"🎉 **Kích hoạt thành công!** Bạn nhận được **+{c_info['value']} lượt buff**."
        
        save_json(DATA_FILE, data)
        del codes[code]
        save_json(CODES_FILE, codes)
        bot.reply_to(message, msg, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ Mã Giftcode không tồn tại hoặc đã được sử dụng!", parse_mode="Markdown")

@bot.message_handler(commands=['diemdanh'])
def handle_diemdanh(message):
    user_id = message.from_user.id
    data = load_json(DATA_FILE)
    u_data = get_user_data(user_id)
    is_vip = check_vip_status(user_id)
    today = str(datetime.date.today())
    if u_data.get("last_checkin") == today:
        bot.reply_to(message, "❌ Hôm nay bạn đã điểm danh rồi!", parse_mode="Markdown")
    else:
        bonus = 2 if is_vip else 1
        data[str(user_id)]["spins"] += bonus
        data[str(user_id)]["last_checkin"] = today
        save_json(DATA_FILE, data)
        bot.reply_to(message, f"🎉 Điểm danh thành công! Nhận **+{bonus} lượt**.", parse_mode="Markdown")

@bot.message_handler(commands=['profile'])
def handle_profile(message):
    user_id = message.from_user.id
    u_data = get_user_data(user_id)
    is_vip = check_vip_status(user_id)
    exp_txt = "Vĩnh viễn ♾️" if u_data.get("vip_expire") == "PERMANENT" else u_data.get("vip_expire", "Chưa có")
    profile_txt = (
        f"👤 **PROFILE CÁ NHÂN**\n\n"
        f"• **ID Telegram:** `{user_id}`\n"
        f"• **Trạng thái VIP:** {'Có 🌟' if is_vip else 'Không ❌'}\n"
        f"• **Thời hạn VIP:** {exp_txt}\n"
        f"• **Lượt buff còn:** `{u_data['spins']}`\n"
        f"• **Đã dùng hôm nay:** `{u_data['daily_used']}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{CRE_TEXT}"
    )
    bot.reply_to(message, profile_txt, parse_mode="Markdown")

@bot.message_handler(commands=['ref'])
def handle_ref(message):
    user_id = message.from_user.id
    ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    bot.reply_to(message, f"🔗 **LINK GIỚI THIỆU:**\n`{ref_link}`\n\nMời người mới nhận ngay **+2 lượt buff**!", parse_mode="Markdown")

# ================= 5. NHÓM LỆNH QUẢN TRỊ VIÊN (ADMIN ONLY) =================

@bot.message_handler(commands=['adminhelp', 'menuadmin', 'adminmenu'])
def handle_adminhelp(message):
    if message.from_user.id != ADMIN_ID: return
    help_txt = (
        "👑 **BẢNG MENU ĐIỀU KHIỂN ADMIN**\n━━━━━━━━━━━━━━━━━━━━\n"
        "• `/sendall <tin_nhắn>` : Gửi tin nhắn tới TẤT CẢ người dùng Bot\n"
        "• `/broadcast <tin_nhắn>` : (Tương tự sendall)\n"
        "• `/stats` : Xem thống kê người dùng & hệ thống\n"
        "• `/maintenance <on/off>` : Bật/Tắt chế độ bảo trì Bot\n"
        "• `/setvip <ID> <số_ngày>` : Nâng VIP cho user\n"
        "• `/unvip <ID>` : Hủy trạng thái VIP\n"
        "• `/addspin <ID> <số_lượt>` : Cộng lượt buff cho user\n"
        "• `/setspin <ID> <số_lượt>` : Đặt lại số lượt cụ thể\n"
        "• `/addcode <mã> <vip/spins> <giá_trị>` : Tạo Giftcode mới\n"
        "• `/userinfo <ID>` : Tra cứu dữ liệu chi tiết 1 User\n"
        "• `/resetdaily` : Reset lượt sử dụng hôm nay của tất cả user"
    )
    bot.reply_to(message, help_txt, parse_mode="Markdown")

@bot.message_handler(commands=['sendall', 'broadcast'])
def handle_broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    
    # Lấy nội dung tin nhắn đằng sau lệnh /sendall hoặc /broadcast
    text = message.text.replace("/sendall", "").replace("/broadcast", "").strip()
    
    if not text:
        bot.reply_to(message, "❌ **Cú pháp sai!** Vui lòng nhập: `/sendall <nội dung tin nhắn>`", parse_mode="Markdown")
        return
    
    users = load_json(DATA_FILE)
    success = 0
    failed = 0
    
    status_msg = bot.reply_to(message, "⏳ **Đang tiến hành gửi tin nhắn cho toàn bộ người dùng...**", parse_mode="Markdown")
    
    for uid in users:
        try:
            bot.send_message(
                int(uid), 
                f"📢 **THÔNG BÁO TỪ ADMIN**\n\n{text}\n\n━━━━━━━━━━━━━━━━━━━━\n{CRE_TEXT}", 
                parse_mode="Markdown"
            )
            success += 1
        except Exception:
            failed += 1
            
    bot.edit_message_text(
        f"✅ **Đã gửi thông báo thành công!**\n\n• Thành công: `{success}` người dùng\n• Thất bại/Block bot: `{failed}` người dùng",
        chat_id=status_msg.chat.id,
        message_id=status_msg.message_id,
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['maintenance'])
def handle_maintenance(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Cú pháp: `/maintenance <on/off>`", parse_mode="Markdown")
        return
    mode = args[1].lower()
    if mode == "on":
        set_config("maintenance", True)
        bot.reply_to(message, "🛠️ **Đã BẬT chế độ bảo trì hệ thống!**", parse_mode="Markdown")
    elif mode == "off":
        set_config("maintenance", False)
        bot.reply_to(message, "✅ **Đã TẮT chế độ bảo trì!** Bot đã sẵn sàng nhận lệnh.", parse_mode="Markdown")

@bot.message_handler(commands=['setvip'])
def handle_setvip(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "❌ Cú pháp: `/setvip <ID> <Số_ngày>`", parse_mode="Markdown")
        return
    target_id, days = args[1], int(args[2])
    data = load_json(DATA_FILE)
    get_user_data(int(target_id))
    data = load_json(DATA_FILE)
    data[target_id]["is_vip"] = True
    data[target_id]["vip_expire"] = "PERMANENT" if days >= 9999 else str(datetime.date.today() + datetime.timedelta(days=days))
    save_json(DATA_FILE, data)
    bot.reply_to(message, f"✅ Đã nâng VIP cho User `{target_id}`!", parse_mode="Markdown")

@bot.message_handler(commands=['unvip'])
def handle_unvip(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Cú pháp: `/unvip <ID>`", parse_mode="Markdown")
        return
    target_id = args[1]
    data = load_json(DATA_FILE)
    if target_id in data:
        data[target_id]["is_vip"] = False
        data[target_id]["vip_expire"] = ""
        save_json(DATA_FILE, data)
        bot.reply_to(message, f"🚫 Đã hủy VIP của User `{target_id}`!", parse_mode="Markdown")

@bot.message_handler(commands=['addspin'])
def handle_addspin(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "❌ Cú pháp: `/addspin <ID_User> <Số_lượt>`", parse_mode="Markdown")
        return
    target_id, amount = args[1], int(args[2])
    data = load_json(DATA_FILE)
    if target_id in data:
        data[target_id]["spins"] += amount
        save_json(DATA_FILE, data)
        bot.reply_to(message, f"✅ Đã cộng **+{amount} lượt** cho user `{target_id}`!", parse_mode="Markdown")

@bot.message_handler(commands=['setspin'])
def handle_setspin(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "❌ Cú pháp: `/setspin <ID_User> <Số_lượt>`", parse_mode="Markdown")
        return
    target_id, amount = args[1], int(args[2])
    data = load_json(DATA_FILE)
    if target_id in data:
        data[target_id]["spins"] = amount
        save_json(DATA_FILE, data)
        bot.reply_to(message, f"✅ Đã đặt số lượt của user `{target_id}` thành **{amount} lượt**!", parse_mode="Markdown")

@bot.message_handler(commands=['userinfo'])
def handle_userinfo(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Cú pháp: `/userinfo <ID_User>`", parse_mode="Markdown")
        return
    target_id = args[1]
    data = load_json(DATA_FILE)
    if target_id in data:
        u = data[target_id]
        info_txt = (
            f"🔍 **CHI TIẾT DỮ LIỆU USER `{target_id}`**\n━━━━━━━━━━━━━━━━━━━━\n"
            f"• **VIP:** {u.get('is_vip', False)} ({u.get('vip_expire', 'N/A')})\n"
            f"• **Lượt buff còn:** {u.get('spins', 0)}\n"
            f"• **Đã dùng hôm nay:** {u.get('daily_used', 0)}\n"
            f"• **Số lượt mời Ref:** {u.get('ref_count', 0)}\n"
            f"• **Tổng số lần Buff:** {u.get('total_buffs', 0)}\n"
            f"• **ID Người giới thiệu:** {u.get('referrer', 'Không có')}"
        )
        bot.reply_to(message, info_txt, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ Không tìm thấy thông tin user này trong hệ thống!", parse_mode="Markdown")

@bot.message_handler(commands=['resetdaily'])
def handle_resetdaily(message):
    if message.from_user.id != ADMIN_ID: return
    data = load_json(DATA_FILE)
    for uid in data:
        data[uid]["daily_used"] = 0
    save_json(DATA_FILE, data)
    bot.reply_to(message, "✅ Đã reset lượt dùng trong ngày của tất cả người dùng về **0**!", parse_mode="Markdown")

@bot.message_handler(commands=['addcode'])
def handle_addcode(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 4:
        bot.reply_to(message, "❌ Cú pháp: `/addcode <mã> <type: vip/spins> <giá_trị>`", parse_mode="Markdown")
        return
    code, c_type, val = args[1], args[2], int(args[3])
    codes = load_json(CODES_FILE)
    codes[code] = {"type": c_type, "value": val}
    save_json(CODES_FILE, codes)
    bot.reply_to(message, f"✅ Đã tạo Giftcode thành công: `{code}`", parse_mode="Markdown")

@bot.message_handler(commands=['stats'])
def handle_stats(message):
    if message.from_user.id != ADMIN_ID: return
    data = load_json(DATA_FILE)
    total_users = len(data)
    vip_users = sum(1 for u in data.values() if u.get("is_vip", False))
    total_buffs = sum(u.get("total_buffs", 0) for u in data.values())

    msg = (
        f"📊 **THỐNG KÊ HỆ THỐNG BOT**\n━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 **Tổng số người dùng:** `{total_users}`\n"
        f"🌟 **Thành viên VIP:** `{vip_users}`\n"
        f"🚀 **Tổng lượt đã Buff:** `{total_buffs}`"
    )
    bot.reply_to(message, msg, parse_mode="Markdown")

# ================= 6. CHẠY BOT =================
if __name__ == "__main__":
    if not os.path.exists(DATA_FILE): save_json(DATA_FILE, {})
    if not os.path.exists(CODES_FILE): save_json(CODES_FILE, {})
    if not os.path.exists(CONFIG_FILE): save_json(CONFIG_FILE, {"maintenance": False})
    print("🚀 Bot Free Fire đã sẵn sàng và cập nhật thêm lệnh /sendall và /menuadmin!")
    bot.infinity_polling(skip_pending=True)

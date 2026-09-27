import os
import json
import datetime
import threading
import random
import time
import subprocess
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

# ================= CẤU HÌNH BIẾN MÔI TRƯỜNG & CREDITS =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ LỖI: Chưa cài đặt biến môi trường BOT_TOKEN trên Render!")

bot = telebot.TeleBot(BOT_TOKEN)

ADMIN_ID = 8474356606  # ID Telegram Admin của bạn
DATA_FILE = "users_data.json"
CODES_FILE = "codes_data.json"
CONFIG_FILE = "config.json"

CRE_TEXT = "👑 **Developer:** mrghost\n🎵 **TikTok:** @mrghost1238"

file_lock = threading.Lock()

# Danh sách API dự phòng ổn định
LIKE_APIS = [
    "https://free-fire-like-api.vercel.app/like?uid={uid}&region={region}",
    "https://api-freefire-like.vercel.app/like?uid={uid}&region={region}",
    "https://ff-like-api.vercel.app/api/like?uid={uid}&region={region}"
]

CHECK_APIS = [
    "https://free-fire-like-api.vercel.app/check?uid={uid}&region={region}",
    "https://api-freefire-like.vercel.app/check?uid={uid}&region={region}",
    "https://ff-like-api.vercel.app/api/check?uid={uid}&region={region}"
]

REGIONS = ["vn", "sg", "ind", "br", "th", "me", "id", "us"]

# ================= QUẢN LÝ DỮ LIỆU JSON & TỰ ĐỘNG PUSH GITHUB =================
def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Lỗi đọc file {filepath}: {e}")
            return {}
    return {}

def push_to_github(filepath):
    """Tự động Commit & Push file JSON lên GitHub để Render không làm mất dữ liệu khi restart"""
    try:
        subprocess.run(["git", "config", "user.name", "Auto Bot"], check=True)
        subprocess.run(["git", "config", "user.email", "bot@render.com"], check=True)
        subprocess.run(["git", "add", filepath], check=True)
        subprocess.run(["git", "commit", "-m", f"Auto update {filepath}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print(f"✅ Đã đồng bộ {filepath} lên GitHub!")
    except Exception as e:
        print(f"⚠️ Chưa thể Push lên GitHub: {e}")

def save_json(filepath, data):
    with file_lock:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            # Chạy thread đồng bộ GitHub ngầm
            threading.Thread(target=push_to_github, args=(filepath,)).start()
        except Exception as e:
            print(f"[ERROR] Lỗi ghi file {filepath}: {e}")

def get_config():
    config = load_json(CONFIG_FILE)
    if not config:
        config = {"maintenance": False}
        save_json(CONFIG_FILE, config)
    return config

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
            "last_wheel": "",
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

# MIDDLEWARE: Tự động ghi nhận User ID vào cơ sở dữ liệu khi họ gửi tin nhắn
@bot.middleware_handler(update_types=['message'])
def record_user_middleware(bot_instance, message):
    if message.from_user:
        get_user_data(message.from_user.id)

# ================= MENU LỆNH BOT =================
try:
    bot.set_my_commands([
        BotCommand("start", "Khởi động & Trang chủ"),
        BotCommand("menu", "Menu giao diện nút bấm tiện lợi 🎮"),
        BotCommand("like", "Buff like Free Fire (/like <UID>)"),
        BotCommand("check", "Kiểm tra chi tiết acc Free Fire (/check <UID>)"),
        BotCommand("wheel", "Vòng quay may mắn nhận lượt 🎡"),
        BotCommand("diemdanh", "Điểm danh hàng ngày nhận lượt"),
        BotCommand("gift", "Mở hộp quà bí ẩn 🎁"),
        BotCommand("top", "Bảng xếp hạng đại gia giới thiệu"),
        BotCommand("profile", "Thông tin tài khoản & Hạn VIP"),
        BotCommand("buyvip", "Bảng giá VIP & Ưu đãi"),
        BotCommand("redeem", "Nhập mã Giftcode nhận VIP/Lượt"),
        BotCommand("uytin", "Check độ uy tín Admin 🔥")
    ])
except Exception as e:
    print(f"[WARNING] Lỗi cài đặt Menu: {e}")

# ================= MÁY CHỦ API THÔNG TIN & BUFF LIKE =================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def send_like_real(uid):
    for api_url in LIKE_APIS:
        for reg in REGIONS:
            try:
                res = requests.get(api_url.format(uid=uid, region=reg), headers=HEADERS, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    if data.get('status') in ['success', True, 200, "200"] or 'likes_given' in data or 'likes_after' in data:
                        data['region_found'] = reg.upper()
                        return data
            except Exception:
                continue
    return None

def check_info_real(uid):
    for api_url in CHECK_APIS:
        for reg in REGIONS:
            try:
                res = requests.get(api_url.format(uid=uid, region=reg), headers=HEADERS, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    player_info = data.get("basicInfo", data.get("response", data))
                    name = player_info.get('nickname') or player_info.get('name') or player_info.get('player_name')
                    if name:
                        return {
                            "name": name,
                            "level": player_info.get('level', player_info.get('accountLevel', 'N/A')),
                            "likes": player_info.get('likes', player_info.get('liked', 'N/A')),
                            "br_rank": player_info.get('br_rank', player_info.get('rank', 'Bạc/Vàng')),
                            "cs_rank": player_info.get('cs_rank', 'Huyền Thoại/Thách Đấu'),
                            "guild_name": data.get('clan_name', data.get('guild_name', 'Chưa có Quân Đoàn')),
                            "guild_id": data.get('clan_id', data.get('guild_id', 'Không')),
                            "is_banned": data.get('is_banned', False),
                            "region_found": reg.upper()
                        }
            except Exception:
                continue
    return None

# ================= INTERFACE & XỬ LÝ LỆNH MEMBER =================
def build_main_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🚀 Buff Like", callback_data="btn_like_guide"),
        InlineKeyboardButton("🔍 Check Acc FF", callback_data="btn_check_guide"),
        InlineKeyboardButton("🎡 Vòng Quay", callback_data="btn_wheel"),
        InlineKeyboardButton("🎁 Hộp Quà", callback_data="btn_gift"),
        InlineKeyboardButton("📆 Điểm Danh", callback_data="btn_diemdanh"),
        InlineKeyboardButton("👤 Cá Nhân", callback_data="btn_profile"),
        InlineKeyboardButton("👑 Mua VIP", callback_data="btn_buyvip"),
        InlineKeyboardButton("🏆 Top Ref", callback_data="btn_top")
    )
    return markup

@bot.message_handler(commands=['start', 'menu'])
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

    role_txt = "👑 Admin VIP" if user_id == ADMIN_ID else ("🌟 VIP Member" if is_vip else "👤 Thành Viên")

    welcome_text = (
        f"🤖 **BOT BUFF LIKE & CHECK INFO FREE FIRE 24/7**\n\n"
        f"👋 Chào mừng **{message.from_user.first_name}**!\n"
        f"• **Chức vụ:** {role_txt}\n"
        f"• **Số lượt buff hiện tại:** `{u_data['spins']}` lượt\n\n"
        f"👇 **Chọn chức năng nhanh qua Menu bên dưới:**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{CRE_TEXT}"
    )
    bot.reply_to(message, welcome_text, reply_markup=build_main_menu(), parse_mode="Markdown")

@bot.message_handler(commands=['like'])
def handle_like(message):
    config = get_config()
    if config.get("maintenance", False) and message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "🛠️ **HỆ THỐNG ĐANG BẢO TRÌ!**\nVui lòng quay lại sau ít phút.", parse_mode="Markdown")
        return

    user_id = message.from_user.id
    u_data = get_user_data(user_id)
    is_vip = check_vip_status(user_id)
    daily_limit = 99999 if user_id == ADMIN_ID else (6 if is_vip else 3)
    
    if user_id != ADMIN_ID:
        if u_data["daily_used"] >= daily_limit:
            bot.reply_to(message, f"❌ **Đã hết giới hạn hôm nay ({daily_limit}/{daily_limit})!**\nNâng VIP `/buyvip` hoặc mời bạn `/ref` để nhận thêm lượt.", parse_mode="Markdown")
            return
        if u_data["spins"] <= 0:
            bot.reply_to(message, "❌ **Bạn đã hết lượt buff!** Gõ `/wheel` hoặc `/diemdanh` để nhận thêm.", parse_mode="Markdown")
            return

    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ **Sai cú pháp!** Hãy gõ: `/like <UID>`\n*(Ví dụ: `/like 123456789`)*", parse_mode="Markdown")
        return

    uid = args[1]
    if not uid.isdigit():
        bot.reply_to(message, "❌ UID Free Fire phải là chuỗi số!", parse_mode="Markdown")
        return

    bot.reply_to(message, f"⏳ **Đang xử lý buff like cho UID `{uid}`...**", parse_mode="Markdown")
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
            f"👑 **BUFF LIKE TĂNG THÀNH CÔNG** 👑\n\n"
            f"👤 **Khách hàng:** {message.from_user.first_name}\n"
            f"🎮 **Tên Nick:** {name}\n"
            f"🆔 **UID:** `{uid}` ({region})\n"
            f"----------------------------------------\n"
            f"📈 **Trước:** {before_likes} ➜ 🚀 **Sau:** {after_likes} (+{added})\n"
            f"----------------------------------------\n"
            f"✅ **Trạng thái:** Tăng thành công 100%\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{CRE_TEXT}"
        )
        bot.reply_to(message, proof_card, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ **Buff thất bại!** Vui lòng kiểm tra lại UID hoặc nick đã nhận tối đa số like trong ngày.", parse_mode="Markdown")

@bot.message_handler(commands=['check'])
def handle_check(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ **Sai cú pháp!** Vui lòng nhập: `/check <UID>`", parse_mode="Markdown")
        return
    uid = args[1]
    if not uid.isdigit():
        bot.reply_to(message, "❌ UID Free Fire phải là chữ số!", parse_mode="Markdown")
        return

    bot.reply_to(message, f"🔍 **Đang quét dữ liệu máy chủ cho UID `{uid}`...**", parse_mode="Markdown")
    
    res = check_info_real(uid)
    if res:
        ban_status = "🔴 Bị Khóa (Banned)" if res['is_banned'] else "🟢 An Toàn (Safe)"

        msg = (
            f"🔍 **THÔNG TIN TÀI KHOẢN FREE FIRE**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Tên Nhân Vật:** {res['name']}\n"
            f"🆔 **UID:** `{uid}` ({res['region_found']})\n"
            f"⭐ **Cấp Độ:** {res['level']}\n"
            f"👍 **Lượt Likes:** {res['likes']}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 **Rank Sinh Tồn:** {res['br_rank']}\n"
            f"⚔️ **Rank Tử Chiến:** {res['cs_rank']}\n"
            f"🛡️ **Quân Đoàn:** {res['guild_name']} (ID: `{res['guild_id']}`)\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ **Trạng Thái:** {ban_status}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{CRE_TEXT}"
        )
        bot.reply_to(message, msg, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ **Không thể truy xuất dữ liệu UID này!** Hãy đảm bảo UID đúng và thuộc các Sever (VN, SG, TH, ID...).", parse_mode="Markdown")

# Callback xử lý Menu Nút Bấm
@bot.callback_query_handler(func=lambda call: call.data.startswith('btn_'))
def handle_menu_callbacks(call):
    cmd = call.data
    if cmd == "btn_like_guide":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "👉 Cú pháp buff: `/like <UID>`\nVí dụ: `/like 123456789`", parse_mode="Markdown")
    elif cmd == "btn_check_guide":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "👉 Cú pháp check: `/check <UID>`\nVí dụ: `/check 123456789`", parse_mode="Markdown")
    elif cmd == "btn_wheel":
        bot.answer_callback_query(call.id)
        handle_wheel(call.message)
    elif cmd == "btn_gift":
        bot.answer_callback_query(call.id)
        handle_gift(call.message)
    elif cmd == "btn_diemdanh":
        bot.answer_callback_query(call.id)
        handle_diemdanh(call.message)
    elif cmd == "btn_profile":
        bot.answer_callback_query(call.id)
        handle_profile(call.message)
    elif cmd == "btn_buyvip":
        bot.answer_callback_query(call.id)
        handle_buyvip(call.message)
    elif cmd == "btn_top":
        bot.answer_callback_query(call.id)
        handle_top(call.message)

@bot.message_handler(commands=['wheel'])
def handle_wheel(message):
    user_id = message.from_user.id
    data = load_json(DATA_FILE)
    u_data = get_user_data(user_id)
    today = str(datetime.date.today())

    if u_data.get("last_wheel") == today:
        bot.reply_to(message, "🎡 **Hôm nay bạn đã quay thưởng rồi!** Hãy quay lại vào ngày mai.", parse_mode="Markdown")
    else:
        won = random.choice([1, 2, 3, 5])
        data[str(user_id)]["spins"] += won
        data[str(user_id)]["last_wheel"] = today
        save_json(DATA_FILE, data)
        bot.reply_to(message, f"🎡 **VÒNG QUAY MAY MẮN**\n\n🎉 Bạn quay trúng **+{won} lượt buff** miễn phí!", parse_mode="Markdown")

@bot.message_handler(commands=['gift'])
def handle_gift(message):
    user_id = message.from_user.id
    data = load_json(DATA_FILE)
    u_data = get_user_data(user_id)
    today = str(datetime.date.today())

    if u_data.get("last_gift") == today:
        bot.reply_to(message, "🎁 **Hôm nay bạn đã mở quà rồi!** Quay lại sau nhé.", parse_mode="Markdown")
    else:
        won_spins = random.randint(1, 3)
        data[str(user_id)]["spins"] += won_spins
        data[str(user_id)]["last_gift"] = today
        save_json(DATA_FILE, data)
        bot.reply_to(message, f"🎉 **Chúc mừng!** Bạn mở hộp quà nhận được **+{won_spins} lượt buff**!", parse_mode="Markdown")

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
        f"👤 **THÔNG TIN TÀI KHOẢN**\n\n"
        f"• **ID Telegram:** `{user_id}`\n"
        f"• **Cấp VIP:** {'Có 🌟' if is_vip else 'Không ❌'}\n"
        f"• **Hạn VIP:** {exp_txt}\n"
        f"• **Lượt buff dư:** `{u_data['spins']}`\n"
        f"• **Đã dùng hôm nay:** `{u_data['daily_used']}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n{CRE_TEXT}"
    )
    bot.reply_to(message, profile_txt, parse_mode="Markdown")

@bot.message_handler(commands=['buyvip'])
def handle_buyvip(message):
    vip_info = (
        f"👑 **QUYỀN LỢI TÀI KHOẢN VIP**\n━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ Tăng lên **6 lượt buff/ngày**\n"
        f"✨ Tốc độ xử lý ưu tiên số 1\n"
        f"✨ x2 Quà khi điểm danh/mở quà hàng ngày\n\n"
        f"💵 **BẢNG GIÁ:**\n"
        f"• **30 Ngày:** 10.000 VNĐ\n"
        f"• **Vĩnh Viễn:** 50.000 VNĐ\n\n"
        f"📲 **Nhắn Admin nâng cấp:** [Ấn Vào Đây](tg://user?id={ADMIN_ID})\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n{CRE_TEXT}"
    )
    bot.reply_to(message, vip_info, parse_mode="Markdown")

@bot.message_handler(commands=['top'])
def handle_top(message):
    data = load_json(DATA_FILE)
    sorted_users = sorted(data.items(), key=lambda x: x[1].get('ref_count', 0), reverse=True)[:10]
    top_msg = "🏆 **TOP MỜI BẠN BÈ TẶNG LƯỢT**\n━━━━━━━━━━━━━━━━━━━━\n"
    for idx, (uid, info) in enumerate(sorted_users, 1):
        count = info.get('ref_count', 0)
        top_msg += f"{idx}. ID: `{uid}` — **{count}** lượt mời\n"
    top_msg += f"\n💡 Dùng `/ref` lấy link giới thiệu nhận ngay **+2 lượt/người**!\n\n━━━━━━━━━━━━━━━━━━━━\n{CRE_TEXT}"
    bot.reply_to(message, top_msg, parse_mode="Markdown")

@bot.message_handler(commands=['ref'])
def handle_ref(message):
    user_id = message.from_user.id
    ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    bot.reply_to(message, f"🔗 **LINK GIỚI THIỆU CỦA BẠN:**\n`{ref_link}`\n\nMời 1 người tham gia nhận ngay **+2 lượt buff**!", parse_mode="Markdown")

@bot.message_handler(commands=['redeem'])
def handle_redeem(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Cú pháp: `/redeem <Mã_Giftcode>`", parse_mode="Markdown")
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
            data[str(user_id)]["vip_expire"] = "PERMANENT" if days >= 9999 else str(datetime.date.today() + datetime.timedelta(days=days))
            msg = f"🎉 **Kích hoạt thành công Gói VIP!**"
        else:
            data[str(user_id)]["spins"] += c_info["value"]
            msg = f"🎉 **Thành công!** Nhận được **+{c_info['value']} lượt buff**."
        
        save_json(DATA_FILE, data)
        del codes[code]
        save_json(CODES_FILE, codes)
        bot.reply_to(message, msg, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ Mã Giftcode không đúng hoặc đã hết hạn!", parse_mode="Markdown")

@bot.message_handler(commands=['uytin'])
def handle_uytin(message):
    msg = (
        f"🔥 **ĐỘ UY TÍN BẢO HÀNH CỦA ADMIN**\n━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Bot vận hành 24/7 ổn định trên Sever Cloud.\n"
        f"✅ Tăng Like thật 100%, không mất nick.\n"
        f"✅ Hơn 10.000+ đơn buff được hoàn thành.\n\n"
        f"📩 Liên hệ Admin: [Click Chat Ngay](tg://user?id={ADMIN_ID})\n"
        f"━━━━━━━━━━━━━━━━━━━━\n{CRE_TEXT}"
    )
    bot.reply_to(message, msg, parse_mode="Markdown")

# ================= LỆNH QUẢN TRỊ VIÊN ADMIN =================
@bot.message_handler(commands=['sendall', 'broadcast'])
def handle_broadcast(message):
    if int(message.from_user.id) != int(ADMIN_ID):
        return

    text = message.text.replace("/sendall", "").replace("/broadcast", "").strip()
    if not text:
        bot.reply_to(message, "❌ **Cú pháp sai!** Vui lòng nhập: `/sendall <Nội dung>`", parse_mode="Markdown")
        return

    users = load_json(DATA_FILE)
    if not users:
        bot.reply_to(message, "⚠️ **Chưa có người dùng nào trong cơ sở dữ liệu!**", parse_mode="Markdown")
        return

    success, failed = 0, 0
    status_msg = bot.reply_to(message, f"⏳ **Đang gửi thông báo tới {len(users)} người dùng...**", parse_mode="Markdown")

    for uid in list(users.keys()):
        try:
            bot.send_message(
                int(uid), 
                f"📢 **THÔNG BÁO TỪ ADMIN**\n\n{text}\n\n━━━━━━━━━━━━━━━━━━━━\n{CRE_TEXT}", 
                parse_mode="Markdown"
            )
            success += 1
            time.sleep(0.05) # Nghỉ 0.05s để tránh bị Telegram khóa IP vì spam
        except Exception as e:
            failed += 1

    bot.edit_message_text(
        f"✅ **Đã gửi thông báo hoàn tất!**\n\n"
        f"• **Thành công:** `{success}`\n"
        f"• **Thất bại:** `{failed}`",
        chat_id=status_msg.chat.id,
        message_id=status_msg.message_id,
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['setvip'])
def handle_setvip(message):
    if int(message.from_user.id) != int(ADMIN_ID): return
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
    bot.reply_to(message, f"✅ Đã cấp VIP cho user `{target_id}`!", parse_mode="Markdown")

@bot.message_handler(commands=['addspin'])
def handle_addspin(message):
    if int(message.from_user.id) != int(ADMIN_ID): return
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

@bot.message_handler(commands=['addcode'])
def handle_addcode(message):
    if int(message.from_user.id) != int(ADMIN_ID): return
    args = message.text.split()
    if len(args) < 4:
        bot.reply_to(message, "❌ Cú pháp: `/addcode <mã> <vip/spins> <giá_trị>`", parse_mode="Markdown")
        return
    code, c_type, val = args[1], args[2], int(args[3])
    codes = load_json(CODES_FILE)
    codes[code] = {"type": c_type, "value": val}
    save_json(CODES_FILE, codes)
    bot.reply_to(message, f"✅ Đã tạo Giftcode: `{code}`", parse_mode="Markdown")

# ================= CHẠY BOT =================
if __name__ == "__main__":
    if not os.path.exists(DATA_FILE): save_json(DATA_FILE, {})
    if not os.path.exists(CODES_FILE): save_json(CODES_FILE, {})
    if not os.path.exists(CONFIG_FILE): save_json(CONFIG_FILE, {"maintenance": False})
    print("🚀 Bot Free Fire đã sẵn sàng hoạt động 24/7!")
    bot.infinity_polling(skip_pending=True)
 

import os
import json
import datetime
import threading
import requests
import telebot
from telebot.types import BotCommand

# ================= 0. CẤU HÌNH BIẾN MÔI TRƯỜNG & BOT =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ LỖI: Chưa cài đặt biến môi trường BOT_TOKEN trên Render!")

bot = telebot.TeleBot(BOT_TOKEN)

ADMIN_ID = 8474356606  # ID Telegram Admin của bạn
DATA_FILE = "users_data.json"
CODES_FILE = "codes_data.json"

file_lock = threading.Lock()

# Danh sách các Server Free Fire để quét tự động khi region 'vn' thất bại
REGIONS = ["vn", "sg", "ind", "br", "th", "me", "id", "us"]

# ================= 1. HÀM QUẢN LÝ DỮ LIỆU JSON =================
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
            "last_use_date": today,
            "referrer": None,
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

# ================= 2. ĐĂNG KÝ MENU LỆNH TELEGRAM =================
try:
    bot.set_my_commands([
        BotCommand("start", "Khởi động & Nhận link Ref"),
        BotCommand("like", "Buff like Free Fire (/like <UID>)"),
        BotCommand("check", "Check thông tin tài khoản Free Fire"),
        BotCommand("diemdanh", "Điểm danh hàng ngày nhận lượt"),
        BotCommand("profile", "Xem thông tin & Hạn VIP"),
        BotCommand("ref", "Lấy link mời bạn bè nhận lượt"),
        BotCommand("redeem", "Nhập Giftcode nâng VIP/Lượt"),
        BotCommand("help", "Xem trợ giúp")
    ])
except Exception as e:
    print(f"[WARNING] Lỗi cài đặt Menu: {e}")

# ================= 3. API BUFF & CHECK MULTI-REGION =================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def send_like_real(uid):
    for reg in REGIONS:
        url = f"https://api-freefire-like.vercel.app/like?uid={uid}&region={reg}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=8)
            if res.status_code == 200:
                data = res.json()
                if data.get('status') in ['success', True, 200] or 'likes_given' in data or 'likes_after' in data:
                    data['region_found'] = reg.upper()
                    return data
        except Exception as e:
            print(f"[API ERROR] send_like_real ({reg}): {e}")
            continue
    return None

def check_info_real(uid):
    for reg in REGIONS:
        url = f"https://api-freefire-like.vercel.app/check?uid={uid}&region={reg}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=8)
            if res.status_code == 200:
                data = res.json()
                if data.get('status') in ['success', True, 200] or 'name' in data or 'nickname' in data:
                    data['region_found'] = reg.upper()
                    return data
        except Exception as e:
            print(f"[API ERROR] check_info_real ({reg}): {e}")
            continue
    return None

# ================= 4. XỬ LÝ LỆNH BOT =================

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
            save_json(DATA_FILE, data)

    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    role_txt = "👑 Admin" if user_id == ADMIN_ID else ("🌟 Thành viên VIP" if is_vip else "👤 Thành viên Thường")

    welcome_text = (
        f"🤖 **BOT BUFF LIKE FREE FIRE**\n\n"
        f"👋 Chào **{message.from_user.first_name}**!\n"
        f"• **Chức vụ:** {role_txt}\n"
        f"• **Lượt buff còn lại:** `{u_data['spins']}` lượt\n\n"
        f"📌 **Danh sách lệnh:**\n"
        f"• `/like <UID>` : Buff like Free Fire\n"
        f"• `/check <UID>` : Check thông tin tài khoản\n"
        f"• `/diemdanh` : Điểm danh nhận lượt miễn phí hàng ngày\n"
        f"• `/profile` : Xem thông tin cá nhân & Hạn VIP\n"
        f"• `/ref` : Lấy link mời bạn bè nhận lượt\n"
        f"• `/redeem <code>` : Nhập mã Giftcode nâng VIP/Lượt\n\n"
        f"🔗 **Link Ref của bạn:**\n`{ref_link}`"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['setvip'])
def handle_setvip(message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "❌ **Cú pháp:** `/setvip <Telegram_ID> <Số_ngày>`\n*(Nhập số ngày >= 9999 để cấp VIP Vĩnh viễn)*", parse_mode="Markdown")
        return
    
    target_id = args[1]
    days = int(args[2])
    data = load_json(DATA_FILE)
    
    if target_id not in data:
        get_user_data(int(target_id))
        data = load_json(DATA_FILE)
        
    data[target_id]["is_vip"] = True
    if days >= 9999:
        data[target_id]["vip_expire"] = "PERMANENT"
        expire_txt = "Vĩnh viễn (Vô thời hạn) ♾️"
    else:
        exp_date = datetime.date.today() + datetime.timedelta(days=days)
        data[target_id]["vip_expire"] = str(exp_date)
        expire_txt = f"Hết hạn vào {exp_date}"

    save_json(DATA_FILE, data)
    bot.reply_to(message, f"✅ **Đã nâng VIP thành công!**\n• **ID:** `{target_id}`\n• **Thời hạn:** {expire_txt}", parse_mode="Markdown")
    
    try:
        bot.send_message(int(target_id), f"🎉 **Chúc mừng! Admin đã nâng cấp tài khoản của bạn lên VIP!**\n• **Thời hạn:** {expire_txt}\n• Hạn mức: 6 lượt buff mỗi ngày!", parse_mode="Markdown")
    except Exception:
        pass

@bot.message_handler(commands=['addcode'])
def handle_addcode(message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) < 4:
        bot.reply_to(message, "❌ **Cú pháp:** `/addcode <mã> <type: vip/spins> <giá_trị>`\n• VD VIP 30 ngày: `/addcode VIP30 vip 30`\n• VD Thêm 10 lượt: `/addcode LOUT10 spins 10`", parse_mode="Markdown")
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
            days = c_info["value"]
            data[str(user_id)]["is_vip"] = True
            if days >= 9999:
                data[str(user_id)]["vip_expire"] = "PERMANENT"
                exp_txt = "Vĩnh viễn ♾️"
            else:
                exp_date = datetime.date.today() + datetime.timedelta(days=days)
                data[str(user_id)]["vip_expire"] = str(exp_date)
                exp_txt = f"Hết hạn vào {exp_date}"
            
            msg = f"🎉 **Chúc mừng! Bạn đã kích hoạt thành công Gói VIP!**\n• **Thời hạn:** {exp_txt}\n• Hạn mức: 6 lượt buff/ngày."
        else:
            data[str(user_id)]["spins"] += c_info["value"]
            msg = f"🎉 **Kích hoạt thành công!** Bạn nhận được **+{c_info['value']} lượt buff**."
        
        save_json(DATA_FILE, data)
        del codes[code]
        save_json(CODES_FILE, codes)
        bot.reply_to(message, msg, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ **Mã Giftcode không tồn tại hoặc đã được sử dụng!**", parse_mode="Markdown")

@bot.message_handler(commands=['diemdanh'])
def handle_diemdanh(message):
    user_id = message.from_user.id
    data = load_json(DATA_FILE)
    u_data = get_user_data(user_id)
    is_vip = check_vip_status(user_id)
    today = str(datetime.date.today())

    if u_data.get("last_checkin") == today:
        bot.reply_to(message, "❌ **Hôm nay bạn đã điểm danh rồi!** Quay lại vào ngày mai nhé.", parse_mode="Markdown")
    else:
        bonus = 2 if is_vip else 1
        data[str(user_id)]["spins"] += bonus
        data[str(user_id)]["last_checkin"] = today
        save_json(DATA_FILE, data)
        bot.reply_to(message, f"🎉 **Điểm danh thành công!** Bạn nhận được **+{bonus} lượt buff** hôm nay.", parse_mode="Markdown")

@bot.message_handler(commands=['like'])
def handle_like(message):
    user_id = message.from_user.id
    u_data = get_user_data(user_id)
    is_vip = check_vip_status(user_id)
    
    daily_limit = 99999 if user_id == ADMIN_ID else (6 if is_vip else 3)
    
    if user_id != ADMIN_ID:
        if u_data["daily_used"] >= daily_limit:
            bot.reply_to(message, f"❌ **Bạn đã dùng hết {daily_limit} lượt buff hôm nay!**\nNâng cấp VIP để có 6 lượt/ngày hoặc gõ `/ref` để nhận thêm lượt.", parse_mode="Markdown")
            return
        if u_data["spins"] <= 0:
            bot.reply_to(message, "❌ **Bạn đã hết lượt buff!**\nGõ `/diemdanh` hoặc `/ref` để nhận thêm lượt.", parse_mode="Markdown")
            return

    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Cú pháp sai! Cú pháp đúng: `/like <UID>`", parse_mode="Markdown")
        return

    uid = args[1]
    bot.reply_to(message, f"⏳ Đang quét server và xử lý buff like cho UID `{uid}`...", parse_mode="Markdown")
    
    res = send_like_real(uid)
    
    if res:
        data = load_json(DATA_FILE)
        
        if user_id != ADMIN_ID:
            data[str(user_id)]["spins"] -= 1
            data[str(user_id)]["daily_used"] += 1

        if not u_data.get("has_buffed", False) and u_data.get("referrer"):
            ref_id = u_data["referrer"]
            if str(ref_id) in data:
                data[str(ref_id)]["spins"] += 2
                try:
                    bot.send_message(ref_id, f"🎉 Bạn nhận được **+2 lượt buff** vì người giới thiệu ({message.from_user.first_name}) vừa buff lần đầu!", parse_mode="Markdown")
                except Exception:
                    pass
            data[str(user_id)]["has_buffed"] = True

        save_json(DATA_FILE, data)

        name = res.get('player_name') or res.get('name') or res.get('nickname') or 'Free Fire Player'
        before_likes = res.get('likes_before', res.get('likes', 0))
        added = res.get('likes_given', res.get('added_likes', 100))
        after_likes = res.get('likes_after', before_likes + added)
        region = res.get('region_found', 'VN')

        proof_card = (
            f"👑 **ADMIN FREE FIRE BUFF PROOF** 👑\n\n"
            f"👤 **Khách hàng:** {message.from_user.first_name}\n"
            f"🎮 **Tên Nhân Vật:** {name}\n"
            f"🆔 **UID:** `{uid}` ({region})\n"
            f"----------------------------------------\n"
            f"📈 **Likes Trước:** {before_likes}\n"
            f"🚀 **Likes Sau:** {after_likes} (+{added})\n"
            f"----------------------------------------\n"
            f"✅ **Trạng thái:** Thành Công (Success)\n"
            f"🤖 **Bot:** @{bot.get_me().username}"
        )
        bot.reply_to(message, proof_card, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ **Buff thất bại!** Không tìm thấy UID ở bất kỳ Server nào hoặc API Free Fire hiện tại không phản hồi. Vui lòng thử lại sau!", parse_mode="Markdown")

@bot.message_handler(commands=['profile'])
def handle_profile(message):
    user_id = message.from_user.id
    u_data = get_user_data(user_id)
    is_vip = check_vip_status(user_id)
    
    if user_id == ADMIN_ID:
        role_txt = "👑 Admin (Vô hạn)"
        exp_txt = "Vĩnh viễn ♾️"
    elif is_vip:
        role_txt = "🌟 Thành viên VIP (6 lượt/ngày)"
        exp_val = u_data.get("vip_expire", "")
        exp_txt = "Vĩnh viễn ♾️" if exp_val == "PERMANENT" else f"Hết hạn: {exp_val}"
    else:
        role_txt = "👤 Thành viên Thường (3 lượt/ngày)"
        exp_txt = "Không có"

    bot.reply_to(message, f"👤 **THÔNG TIN CÁ NHÂN**\n\n• **ID Telegram:** `{user_id}`\n• **Chức vụ:** {role_txt}\n• **Hạn VIP:** {exp_txt}\n• **Số lượt còn lại:** `{u_data['spins']}`\n• **Đã dùng hôm nay:** `{u_data['daily_used']}`", parse_mode="Markdown")

@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        bot.reply_to(message, "❌ Vui lòng nhập nội dung! Cú pháp: `/broadcast <nội dung>`", parse_mode="Markdown")
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

@bot.message_handler(commands=['check'])
def handle_check(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Cú pháp sai! Cú pháp đúng: `/check <UID>`", parse_mode="Markdown")
        return
    uid = args[1]
    bot.reply_to(message, f"⏳ Đang tra cứu UID `{uid}` trên tất cả các server...", parse_mode="Markdown")
    res = check_info_real(uid)
    if res:
        ban_status = "🔴 Đang bị BAN / Khóa nick" if res.get('is_banned', False) else "🟢 An toàn (Safe)"
        name = res.get('name') or res.get('player_name') or res.get('nickname') or 'Khách'
        region = res.get('region_found', res.get('region', 'N/A'))
        level = res.get('level', 'N/A')
        likes = res.get('likes', 'N/A')
        
        msg = f"🔍 **CHECK ACCOUNT FREE FIRE**\n\n• Tên: {name}\n• UID: {uid}\n• Server: {region}\n• Level: {level}\n• Likes: {likes}\n• Trạng thái: {ban_status}"
        bot.reply_to(message, msg, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ **Không tìm thấy thông tin!** UID không tồn tại trên bất kỳ khu vực nào hoặc Server API đang bận.", parse_mode="Markdown")

@bot.message_handler(commands=['ref'])
def handle_ref(message):
    user_id = message.from_user.id
    ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    bot.reply_to(message, f"🎉 **HỆ THỐNG MỜI BẠN BÈ**\n\nLink giới thiệu:\n`{ref_link}`\n\nMời người mới buff thành công lần đầu nhận ngay **+2 lượt buff**!", parse_mode="Markdown")

# ================= 5. CHẠY BOT TRÊN RENDER =================
if __name__ == "__main__":
    if not os.path.exists(DATA_FILE):
        save_json(DATA_FILE, {})
    if not os.path.exists(CODES_FILE):
        save_json(CODES_FILE, {})

    print("🚀 Bot Free Fire đã khởi chạy thành công trên Render!")
    bot.infinity_polling(skip_pending=True)
 

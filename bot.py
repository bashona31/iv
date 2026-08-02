import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
import re

# Configuration
TOKEN = "8867778383:AAGKHcZdr4mA7bX2Tl4AO_LOrqjelOlTqt4"
ADMIN_ID = "903018274"

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Data file
DATA_FILE = "data.json"

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"numbers": [], "used_otps": []}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Colorful keyboards
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📱 Get OTP 🎯", callback_data="get_otp")],
        [InlineKeyboardButton("👑 Admin Panel ⚙️", callback_data="admin_panel")],
        [InlineKeyboardButton("ℹ️ About 📖", callback_data="about")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_user_dashboard(number_data):
    keyboard = [
        [InlineKeyboardButton(f"📱 {number_data['number']}", callback_data="no_action")],
        [InlineKeyboardButton(f"🔑 {number_data['password']}", callback_data=f"copy_{number_data['password']}")],
        [InlineKeyboardButton(f"🔢 {number_data['otp']}", callback_data=f"copy_{number_data['otp']}")],
        [InlineKeyboardButton("🔄 New OTP ✨", callback_data="get_new_otp")],
        [InlineKeyboardButton("🔙 Back ⬅️", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_panel():
    keyboard = [
        [InlineKeyboardButton("📤 Upload 📂", callback_data="upload_numbers")],
        [InlineKeyboardButton("📋 View All 👁️", callback_data="view_numbers")],
        [InlineKeyboardButton("🗑️ Delete ❌", callback_data="delete_all")],
        [InlineKeyboardButton("🔙 Back ⬅️", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def start(update: Update, context: CallbackContext):
    welcome_text = """
🌈 <b>🌟 Welcome to OTP Bot!</b> 🌟

<font color="#4ECDC4">━━━━━━━━━━━━━━━━━━</font>

<font color="#FFE66D">🔹</font> <b>Get instant OTP and Password</b>
<font color="#FFE66D">🔹</font> <b>One-tap copy to clipboard</b>
<font color="#FFE66D">🔹</font> <b>Secure and Fast</b>

<font color="#4ECDC4">━━━━━━━━━━━━━━━━━━</font>

<i>👇 Click below to get started!</i>
    """
    
    update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = str(query.from_user.id)
    data = query.data
    current_data = load_data()
    
    if data.startswith("copy_"):
        text_to_copy = data.replace("copy_", "")
        query.edit_message_text(
            f"✅ <b><font color='#00FF00'>Copied!</font></b>\n\n<code>{text_to_copy}</code>",
            parse_mode='HTML'
        )
        return
    
    if data == "back_to_main":
        query.edit_message_text(
            "🌟 <b><font color='#FF6B6B'>Main Menu</font></b>",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return
    
    if data == "get_otp":
        if not current_data["numbers"]:
            query.edit_message_text(
                "❌ <b><font color='#FF0000'>No OTP available!</font></b>",
                reply_markup=get_main_keyboard(),
                parse_mode='HTML'
            )
            return
        
        available_numbers = [n for n in current_data["numbers"] if n["number"] not in current_data["used_otps"]]
        
        if not available_numbers:
            query.edit_message_text(
                "❌ <b><font color='#FF0000'>All OTPs used!</font></b>",
                reply_markup=get_main_keyboard(),
                parse_mode='HTML'
            )
            return
        
        selected = available_numbers[0]
        current_data["used_otps"].append(selected["number"])
        save_data(current_data)
        
        query.edit_message_text(
            f"✅ <b><font color='#00FF00'>Your OTP Details</font></b>\n\n"
            f"<font color='#4ECDC4'>━━━━━━━━━━━━━━━━━━</font>\n\n"
            f"📱 <b>Number:</b> <code>{selected['number']}</code>\n"
            f"🔑 <b>Password:</b> <code>{selected['password']}</code>\n"
            f"🔢 <b>OTP:</b> <code>{selected['otp']}</code>\n\n"
            f"<i>💡 Tap any button to copy</i>",
            reply_markup=get_user_dashboard(selected),
            parse_mode='HTML'
        )
        return
    
    if data == "get_new_otp":
        available_numbers = [n for n in current_data["numbers"] if n["number"] not in current_data["used_otps"]]
        
        if not available_numbers:
            query.edit_message_text(
                "❌ <b><font color='#FF0000'>No more OTPs!</font></b>",
                reply_markup=get_main_keyboard(),
                parse_mode='HTML'
            )
            return
        
        selected = available_numbers[0]
        current_data["used_otps"].append(selected["number"])
        save_data(current_data)
        
        query.edit_message_text(
            f"✨ <b><font color='#FFD700'>New OTP!</font></b> ✨\n\n"
            f"<font color='#4ECDC4'>━━━━━━━━━━━━━━━━━━</font>\n\n"
            f"📱 <b>Number:</b> <code>{selected['number']}</code>\n"
            f"🔑 <b>Password:</b> <code>{selected['password']}</code>\n"
            f"🔢 <b>OTP:</b> <code>{selected['otp']}</code>",
            reply_markup=get_user_dashboard(selected),
            parse_mode='HTML'
        )
        return
    
    if data == "admin_panel":
        if user_id != ADMIN_ID:
            query.edit_message_text(
                "⛔ <b><font color='#FF0000'>Unauthorized!</font></b>",
                parse_mode='HTML'
            )
            return
        
        query.edit_message_text(
            "👑 <b><font color='#FFD700'>Admin Panel</font></b> ⚙️\n\n"
            "<i>Choose an action:</i>",
            reply_markup=get_admin_panel(),
            parse_mode='HTML'
        )
        return
    
    if data == "upload_numbers":
        if user_id != ADMIN_ID:
            query.edit_message_text("⛔ Unauthorized!", parse_mode='HTML')
            return
        
        query.edit_message_text(
            "📤 <b><font color='#FFD700'>Upload Numbers</font></b>\n\n"
            "Send .txt file with format:\n"
            "<code>Number|OTP|Password</code>\n\n"
            "Example:\n"
            "<code>+8801712345678|123456|pass123</code>",
            parse_mode='HTML'
        )
        context.user_data['waiting_for_file'] = True
        return
    
    if data == "view_numbers":
        if user_id != ADMIN_ID:
            query.edit_message_text("⛔ Unauthorized!", parse_mode='HTML')
            return
        
        if not current_data["numbers"]:
            query.edit_message_text("📭 <b>No numbers uploaded</b>", parse_mode='HTML')
            return
        
        text = "📋 <b><font color='#FFD700'>All Numbers</font></b>\n\n"
        for i, num in enumerate(current_data["numbers"], 1):
            status = "✅ USED" if num["number"] in current_data["used_otps"] else "🟢 AVAILABLE"
            text += f"{i}. <code>{num['number']}</code>\n   OTP: <code>{num['otp']}</code> | {status}\n\n"
        
        query.edit_message_text(text, parse_mode='HTML')
        return
    
    if data == "delete_all":
        if user_id != ADMIN_ID:
            query.edit_message_text("⛔ Unauthorized!", parse_mode='HTML')
            return
        
        current_data["numbers"] = []
        current_data["used_otps"] = []
        save_data(current_data)
        query.edit_message_text(
            "🗑️ <b><font color='#FF6B6B'>All data deleted!</font></b>",
            parse_mode='HTML'
        )
        return
    
    if data == "about":
        query.edit_message_text(
            "ℹ️ <b><font color='#FFD700'>About</font></b>\n\n"
            "<b>Version:</b> 2.0 🚀\n"
            "✅ One-tap copy\n"
            "✅ Auto OTP distribution\n"
            "✅ Admin panel\n\n"
            "<i>Made with ❤️</i>",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return

def file_handler(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    
    if user_id != ADMIN_ID:
        update.message.reply_text("⛔ Unauthorized!", parse_mode='HTML')
        return
    
    if not context.user_data.get('waiting_for_file'):
        update.message.reply_text(
            "⚠️ Use 'Upload Numbers' button first!",
            parse_mode='HTML'
        )
        return
    
    document = update.message.document
    if not document.file_name.endswith('.txt'):
        update.message.reply_text(
            "❌ Upload .txt file only!",
            parse_mode='HTML'
        )
        return
    
    file = document.get_file()
    file_content = file.download_as_bytearray()
    content = file_content.decode('utf-8')
    
    lines = content.strip().split('\n')
    new_numbers = []
    
    for line in lines:
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 3:
                new_numbers.append({
                    "number": parts[0].strip(),
                    "otp": parts[1].strip(),
                    "password": parts[2].strip()
                })
    
    current_data = load_data()
    current_data["numbers"].extend(new_numbers)
    save_data(current_data)
    
    update.message.reply_text(
        f"✅ <b><font color='#00FF00'>Uploaded {len(new_numbers)} numbers!</font></b>\n\n"
        f"📊 Total: {len(current_data['numbers'])}",
        parse_mode='HTML'
    )
    
    context.user_data['waiting_for_file'] = False

def main():
    print("🤖 Bot is starting...")
    
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.document, file_handler))
    
    print("🚀 Bot is running...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

import os
import json
import logging
import asyncio
import sys
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import re

# Configuration
TOKEN = "8867778383:AAHB8pBhFfzt4GUGUtj5ASzwuVwFNDLxcp0"  # Your bot token
ADMIN_ID = "903018274"  # Your Telegram user ID

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Data file
DATA_FILE = "data.json"

# Data load/save functions
def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"numbers": [], "used_otps": []}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Colorful emoji and text decorations
def color_text(text, color_code):
    """HTML color formatting for Telegram"""
    return f'<b><font color="{color_code}">{text}</font></b>'

# Main keyboard with colors and emojis
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📱 Get OTP 🎯", callback_data="get_otp")],
        [InlineKeyboardButton("👑 Admin Panel ⚙️", callback_data="admin_panel")],
        [InlineKeyboardButton("ℹ️ About 📖", callback_data="about")]
    ]
    return InlineKeyboardMarkup(keyboard)

# User dashboard with colorful emojis
def get_user_dashboard(number_data):
    keyboard = [
        [InlineKeyboardButton(f"📱 Number: {number_data['number']}", callback_data="no_action")],
        [InlineKeyboardButton(f"🔑 Password: {number_data['password']}", callback_data=f"copy_{number_data['password']}")],
        [InlineKeyboardButton(f"🔢 OTP: {number_data['otp']}", callback_data=f"copy_{number_data['otp']}")],
        [InlineKeyboardButton("🔄 Get New OTP ✨", callback_data="get_new_otp")],
        [InlineKeyboardButton("🔙 Back ⬅️", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Admin panel with colors
def get_admin_panel():
    keyboard = [
        [InlineKeyboardButton("📤 Upload Numbers 📂", callback_data="upload_numbers")],
        [InlineKeyboardButton("📋 View All Numbers 👁️", callback_data="view_numbers")],
        [InlineKeyboardButton("🗑️ Delete All ❌", callback_data="delete_all")],
        [InlineKeyboardButton("🔙 Back ⬅️", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Start command with colorful design
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🌈 <b><font color="#FF6B6B">🌟 Welcome to OTP Bot!</font></b> 🌟

<font color="#4ECDC4">━━━━━━━━━━━━━━━━━━</font>

<font color="#FFE66D">🔹</font> <b>Get instant OTP and Password</b>
<font color="#FFE66D">🔹</font> <b>One-tap copy to clipboard</b>
<font color="#FFE66D">🔹</b> <b>Secure and Fast</b>

<font color="#4ECDC4">━━━━━━━━━━━━━━━━━━</font>

<font color="#A8E6CF">👇 Click below to get started!</font>
    """
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )

# Button click handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data
    current_data = load_data()
    
    # Copy handler with colorful confirmation
    if data.startswith("copy_"):
        text_to_copy = data.replace("copy_", "")
        await query.edit_message_text(
            f"✅ <b><font color='#00FF00'>Copied Successfully!</font></b>\n\n"
            f"<code>{text_to_copy}</code>\n\n"
            f"<i>Press Ctrl+C to copy or tap and hold to select.</i>",
            parse_mode='HTML'
        )
        await query.message.reply_text(
            f"📋 <b><font color='#FFD700'>Copied!</font></b>\n\n"
            f"<code>{text_to_copy}</code>",
            parse_mode='HTML'
        )
        return
    
    # Back to main menu
    if data == "back_to_main":
        await query.edit_message_text(
            "🌟 <b><font color='#FF6B6B'>Main Menu</font></b>",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return
    
    # Get OTP
    if data == "get_otp":
        if not current_data["numbers"]:
            await query.edit_message_text(
                "❌ <b><font color='#FF0000'>No OTP available right now!</font></b>\n\n"
                "<i>Please try again later.</i>",
                reply_markup=get_main_keyboard(),
                parse_mode='HTML'
            )
            return
        
        available_numbers = [n for n in current_data["numbers"] if n["number"] not in current_data["used_otps"]]
        
        if not available_numbers:
            await query.edit_message_text(
                "❌ <b><font color='#FF0000'>All OTPs are used!</font></b>\n\n"
                "<i>Please wait for new ones.</i>",
                reply_markup=get_main_keyboard(),
                parse_mode='HTML'
            )
            return
        
        selected = available_numbers[0]
        current_data["used_otps"].append(selected["number"])
        save_data(current_data)
        
        await query.edit_message_text(
            f"✅ <b><font color='#00FF00'>Your OTP Details</font></b>\n\n"
            f"<font color='#4ECDC4'>━━━━━━━━━━━━━━━━━━</font>\n\n"
            f"📱 <b><font color='#FFD700'>Number:</font></b> <code>{selected['number']}</code>\n"
            f"🔑 <b><font color='#FF6B6B'>Password:</font></b> <code>{selected['password']}</code>\n"
            f"🔢 <b><font color='#A8E6CF'>OTP:</font></b> <code>{selected['otp']}</code>\n\n"
            f"<font color='#4ECDC4'>━━━━━━━━━━━━━━━━━━</font>\n\n"
            f"<i>💡 Tap any button to copy</i>",
            reply_markup=get_user_dashboard(selected),
            parse_mode='HTML'
        )
        return
    
    # Get new OTP
    if data == "get_new_otp":
        if not current_data["numbers"]:
            await query.edit_message_text(
                "❌ <b><font color='#FF0000'>No OTP available!</font></b>",
                parse_mode='HTML'
            )
            return
        
        available_numbers = [n for n in current_data["numbers"] if n["number"] not in current_data["used_otps"]]
        
        if not available_numbers:
            await query.edit_message_text(
                "❌ <b><font color='#FF0000'>No more OTPs available!</font></b>\n\n"
                "<i>Please check back later.</i>",
                reply_markup=get_main_keyboard(),
                parse_mode='HTML'
            )
            return
        
        selected = available_numbers[0]
        current_data["used_otps"].append(selected["number"])
        save_data(current_data)
        
        await query.edit_message_text(
            f"✨ <b><font color='#FFD700'>New OTP Details</font></b> ✨\n\n"
            f"<font color='#4ECDC4'>━━━━━━━━━━━━━━━━━━</font>\n\n"
            f"📱 <b><font color='#FFD700'>Number:</font></b> <code>{selected['number']}</code>\n"
            f"🔑 <b><font color='#FF6B6B'>Password:</font></b> <code>{selected['password']}</code>\n"
            f"🔢 <b><font color='#A8E6CF'>OTP:</font></b> <code>{selected['otp']}</code>\n\n"
            f"<font color='#4ECDC4'>━━━━━━━━━━━━━━━━━━</font>\n\n"
            f"<i>💡 Tap any button to copy</i>",
            reply_markup=get_user_dashboard(selected),
            parse_mode='HTML'
        )
        return
    
    # Admin panel
    if data == "admin_panel":
        if user_id != ADMIN_ID:
            await query.edit_message_text(
                "⛔ <b><font color='#FF0000'>Unauthorized Access!</font></b>\n\n"
                "<i>You don't have permission to access the admin panel.</i>",
                parse_mode='HTML'
            )
            return
        
        await query.edit_message_text(
            "👑 <b><font color='#FFD700'>Admin Panel</font></b> ⚙️\n\n"
            "<font color='#4ECDC4'>━━━━━━━━━━━━━━━━━━</font>\n\n"
            "<i>Choose an action below:</i>",
            reply_markup=get_admin_panel(),
            parse_mode='HTML'
        )
        return
    
    # Upload numbers
    if data == "upload_numbers":
        if user_id != ADMIN_ID:
            await query.edit_message_text(
                "⛔ <b><font color='#FF0000'>Unauthorized!</font></b>",
                parse_mode='HTML'
            )
            return
        
        await query.edit_message_text(
            "📤 <b><font color='#FFD700'>Upload Numbers</font></b> 📂\n\n"
            "<font color='#4ECDC4'>━━━━━━━━━━━━━━━━━━</font>\n\n"
            "<b>Please send a text file (.txt) with the following format:</b>\n\n"
            "<code>Number|OTP|Password</code>\n"
            "<code>Number|OTP|Password</code>\n"
            "<code>Number|OTP|Password</code>\n\n"
            "<b>Example:</b>\n"
            "<code>+8801712345678|123456|pass123</code>\n\n"
            "<font color='#A8E6CF'>📌 Send the file now.</font>",
            parse_mode='HTML'
        )
        context.user_data['waiting_for_file'] = True
        return
    
    # View numbers
    if data == "view_numbers":
        if user_id != ADMIN_ID:
            await query.edit_message_text(
                "⛔ <b><font color='#FF0000'>Unauthorized!</font></b>",
                parse_mode='HTML'
            )
            return
        
        if not current_data["numbers"]:
            await query.edit_message_text(
                "📭 <b><font color='#FFD700'>No numbers uploaded yet.</font></b>",
                parse_mode='HTML'
            )
            return
        
        text = "📋 <b><font color='#FFD700'>All Numbers</font></b>\n\n"
        text += "<font color='#4ECDC4'>━━━━━━━━━━━━━━━━━━</font>\n\n"
        
        for i, num in enumerate(current_data["numbers"], 1):
            used_status = "✅ <font color='#00FF00'>USED</font>" if num["number"] in current_data["used_otps"] else "🟢 <font color='#A8E6CF'>AVAILABLE</font>"
            text += f"<b>{i}.</b> <code>{num['number']}</code>\n"
            text += f"   🔢 OTP: <code>{num['otp']}</code>\n"
            text += f"   🔑 Pass: <code>{num['password']}</code>\n"
            text += f"   {used_status}\n\n"
        
        if len(text) > 4000:
            for i in range(0, len(text), 4000):
                await query.message.reply_text(text[i:i+4000], parse_mode='HTML')
            await query.edit_message_text(
                "📋 <b><font color='#FFD700'>Full list sent above.</font></b>",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(text, parse_mode='HTML')
        return
    
    # Delete all
    if data == "delete_all":
        if user_id != ADMIN_ID:
            await query.edit_message_text(
                "⛔ <b><font color='#FF0000'>Unauthorized!</font></b>",
                parse_mode='HTML'
            )
            return
        
        current_data["numbers"] = []
        current_data["used_otps"] = []
        save_data(current_data)
        await query.edit_message_text(
            "🗑️ <b><font color='#FF6B6B'>All data deleted successfully!</font></b>",
            parse_mode='HTML'
        )
        return
    
    # About
    if data == "about":
        await query.edit_message_text(
            "ℹ️ <b><font color='#FFD700'>About This Bot</font></b> 📖\n\n"
            "<font color='#4ECDC4'>━━━━━━━━━━━━━━━━━━</font>\n\n"
            "<b>Version:</b> 1.0 🚀\n"
            "<b>Created for</b> easy OTP management\n\n"
            "<b><font color='#A8E6CF'>🌟 Features:</font></b>\n"
            "✅ One-tap copy\n"
            "✅ Auto OTP distribution\n"
            "✅ Admin panel\n"
            "✅ Secure & Fast\n\n"
            "<font color='#4ECDC4'>━━━━━━━━━━━━━━━━━━</font>",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return

# File handler
async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ <b><font color='#FF0000'>Unauthorized!</font></b>",
            parse_mode='HTML'
        )
        return
    
    if not context.user_data.get('waiting_for_file'):
        await update.message.reply_text(
            "⚠️ <b><font color='#FFD700'>Please use the 'Upload Numbers' button first.</font></b>",
            parse_mode='HTML'
        )
        return
    
    document = update.message.document
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text(
            "❌ <b><font color='#FF0000'>Please upload a .txt file only!</font></b>",
            parse_mode='HTML'
        )
        return
    
    file = await document.get_file()
    file_content = await file.download_as_bytearray()
    content = file_content.decode('utf-8')
    
    lines = content.strip().split('\n')
    new_numbers = []
    errors = []
    
    for i, line in enumerate(lines, 1):
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 3:
                number = parts[0].strip()
                otp = parts[1].strip()
                password = parts[2].strip()
                new_numbers.append({"number": number, "otp": otp, "password": password})
            else:
                errors.append(f"Line {i}: Invalid format")
        else:
            errors.append(f"Line {i}: Missing '|' separator")
    
    if errors:
        error_text = "❌ <b><font color='#FF0000'>Errors found:</font></b>\n\n"
        error_text += "\n".join([f"• {err}" for err in errors[:5]])
        error_text += "\n\n<i>Please fix and try again.</i>"
        await update.message.reply_text(error_text, parse_mode='HTML')
        return
    
    current_data = load_data()
    current_data["numbers"].extend(new_numbers)
    save_data(current_data)
    
    await update.message.reply_text(
        f"✅ <b><font color='#00FF00'>Successfully uploaded {len(new_numbers)} numbers!</font></b>\n\n"
        f"<font color='#4ECDC4'>━━━━━━━━━━━━━━━━━━</font>\n\n"
        f"📊 <b>Total numbers:</b> <code>{len(current_data['numbers'])}</code>\n"
        f"🟢 <b>Available:</b> <code>{len([n for n in current_data['numbers'] if n['number'] not in current_data['used_otps']])}</code>\n"
        f"✅ <b>Used:</b> <code>{len(current_data['used_otps'])}</code>",
        parse_mode='HTML'
    )
    
    context.user_data['waiting_for_file'] = False

# Custom wrapper to handle Python 3.14 compatibility
async def run_bot():
    print("🤖 Bot is starting...")
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.Document.ALL, file_handler))
    
    print("🚀 Bot is running...")
    
    # Initialize and start the bot
    await application.initialize()
    await application.start()
    
    # Start polling
    await application.updater.start_polling()
    
    # Keep the bot running
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

# Main entry point
def main():
    try:
        if sys.version_info >= (3, 14):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run_bot())
            finally:
                loop.close()
        else:
            asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
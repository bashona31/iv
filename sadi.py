#!/usr/bin/env python3
"""
IVASMS OTP BOT - PRODUCTION READY (FINAL)
No Page Refresh | No Duplicate OTP | Auto Country Detection | Slow Typing
"""

import os
import sys
import time
import asyncio
import re
import json
import random
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from asyncio import Lock, Semaphore
from logging.handlers import RotatingFileHandler

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ========== CONFIGURATION ==========
BOT_TOKEN = "5264213507:AAESDDORGTgny2qPNhZ5O89H8jVZ9BtoF2c"
ADMIN_ID = 903018274
CHAT_ID = -1004242575120

EMAIL = "maiologali350@gmail.com"
PASSWORD = "Abdulla20@"

# ========== SETTINGS ==========
CHECK_INTERVAL = 5  # seconds
PAGE_REFRESH_INTERVAL = 30  # seconds
MAX_RETRIES = 3
OTP_FILE = "sent_otps.json"
LOG_FILE = "bot.log"

# Typing speed settings (in seconds)
MIN_TYPING_DELAY = 0.15
MAX_TYPING_DELAY = 0.35
EXTRA_PAUSE_CHANCE = 0.15  # 15% chance for extra pause
EXTRA_PAUSE_DURATION = 0.5  # seconds

# ========== LOGGING SETUP ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3)
    ]
)
logger = logging.getLogger(__name__)

# ========== GLOBAL VARIABLES ==========
driver = None
sent_otps = {}
sent_otps_lock = Lock()
telegram_semaphore = Semaphore(1)
last_refresh_time = 0
bot_start_time = time.time()

# ========== HUMAN-LIKE TYPING FUNCTION ==========
def slow_type(element, text: str):
    """Type text like a human - with random delays"""
    # Clear the field first
    element.clear()
    time.sleep(random.uniform(0.3, 0.6))
    
    # Type each character with random delay
    for i, char in enumerate(text):
        element.send_keys(char)
        
        # Random delay between keystrokes (0.15 to 0.35 seconds)
        delay = random.uniform(MIN_TYPING_DELAY, MAX_TYPING_DELAY)
        time.sleep(delay)
        
        # Occasionally take a longer pause (like human thinking)
        if random.random() < EXTRA_PAUSE_CHANCE:
            extra_pause = random.uniform(0.3, EXTRA_PAUSE_DURATION)
            time.sleep(extra_pause)
            logger.debug(f"Human-like pause: {extra_pause:.2f}s")
    
    # Small pause after typing
    time.sleep(random.uniform(0.4, 0.8))
    logger.debug(f"✓ Typed: {text[:3]}... (length: {len(text)})")

def slow_type_with_backspace(element, text: str):
    """Type slowly with occasional backspace (more human-like)"""
    element.clear()
    time.sleep(0.5)
    
    for i, char in enumerate(text):
        element.send_keys(char)
        time.sleep(random.uniform(0.12, 0.28))
        
        # 5% chance to make a mistake and correct it
        if random.random() < 0.05 and i > 0:
            # Backspace and retype
            element.send_keys('\b')
            time.sleep(0.2)
            element.send_keys(char)
            time.sleep(0.15)
            logger.debug("Made a typo and corrected")

# ========== COUNTRY DETECTION ==========
COUNTRY_CODES = {
    '880': '🇧🇩 Bangladesh', '1': '🇺🇸 United States', '44': '🇬🇧 United Kingdom',
    '91': '🇮🇳 India', '86': '🇨🇳 China', '81': '🇯🇵 Japan', '82': '🇰🇷 South Korea',
    '49': '🇩🇪 Germany', '33': '🇫🇷 France', '39': '🇮🇹 Italy', '34': '🇪🇸 Spain',
    '55': '🇧🇷 Brazil', '61': '🇦🇺 Australia', '7': '🇷🇺 Russia', '966': '🇸🇦 Saudi Arabia',
    '971': '🇦🇪 UAE', '92': '🇵🇰 Pakistan', '94': '🇱🇰 Sri Lanka', '977': '🇳🇵 Nepal',
    '60': '🇲🇾 Malaysia', '65': '🇸🇬 Singapore', '66': '🇹🇭 Thailand', '84': '🇻🇳 Vietnam'
}

def get_country_from_phone(phone: str) -> str:
    phone_clean = re.sub(r'\D', '', phone)
    for code in sorted(COUNTRY_CODES.keys(), key=len, reverse=True):
        if phone_clean.startswith(code):
            return COUNTRY_CODES[code]
    return '🌍 Unknown'

# ========== OTP EXTRACTION ==========
def extract_otp(text: str) -> Optional[str]:
    if not text:
        return None
    
    # 6 digit OTP
    match = re.search(r'\b(\d{6})\b', text)
    if match:
        return match.group(1)
    
    # 5 digit OTP
    match = re.search(r'\b(\d{5})\b', text)
    if match:
        return match.group(1)
    
    # 4 digit OTP
    match = re.search(r'\b(\d{4})\b', text)
    if match:
        return match.group(1)
    
    # Facebook style: <#> 123456 is your Facebook code
    match = re.search(r'<#>?\s*(\d{5,6})\s+is your', text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Spaced OTP like "123 456"
    match = re.search(r'(\d{3})\s+(\d{3})', text)
    if match:
        return match.group(1) + match.group(2)
    
    return None

def get_service(text: str) -> str:
    text_lower = text.lower()
    if 'facebook' in text_lower:
        return 'Facebook'
    if 'tiktok' in text_lower:
        return 'TikTok'
    if 'google' in text_lower:
        return 'Google'
    if 'whatsapp' in text_lower:
        return 'WhatsApp'
    if 'instagram' in text_lower:
        return 'Instagram'
    if 'telegram' in text_lower:
        return 'Telegram'
    if 'binance' in text_lower:
        return 'Binance'
    return 'SMS Service'

# ========== FILE HANDLING ==========
def load_sent_otps():
    global sent_otps
    if os.path.exists(OTP_FILE):
        try:
            with open(OTP_FILE, 'r') as f:
                sent_otps = json.load(f)
            logger.info(f"Loaded {len(sent_otps)} sent OTPs")
        except:
            sent_otps = {}

def save_sent_otps():
    try:
        with open(OTP_FILE, 'w') as f:
            json.dump(sent_otps, f)
    except Exception as e:
        logger.error(f"Failed to save: {e}")

# ========== BROWSER FUNCTIONS ==========
def init_browser() -> bool:
    global driver
    try:
        logger.info("🌐 Opening browser...")
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        driver = uc.Chrome(options=options)
        logger.info("✅ Browser ready")
        return True
    except Exception as e:
        logger.error(f"❌ Browser error: {e}")
        return False

def login() -> bool:
    global driver
    try:
        logger.info("🔐 Logging in to ivasms.com...")
        driver.get("https://www.ivasms.com/login")
        time.sleep(5)
        
        if "portal" in driver.current_url:
            logger.info("✅ Already logged in")
            return True
        
        # Email field - TYPE SLOWLY
        logger.info("📧 Entering email (slow typing)...")
        email_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "email"))
        )
        slow_type(email_field, EMAIL)
        logger.info("✓ Email entered")
        
        # Small random pause between email and password
        time.sleep(random.uniform(1.0, 2.0))
        
        # Password field - TYPE SLOWLY
        logger.info("🔑 Entering password (slow typing)...")
        password_field = driver.find_element(By.NAME, "password")
        slow_type(password_field, PASSWORD)
        logger.info("✓ Password entered")
        
        # Wait before clicking login
        time.sleep(random.uniform(1.0, 1.5))
        
        # Login button
        logger.info("👆 Clicking login button...")
        login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_btn.click()
        
        # Wait for redirect
        logger.info("⏳ Waiting for login to complete...")
        time.sleep(10)
        
        if "portal" in driver.current_url:
            logger.info("✅ Login successful!")
            return True
        else:
            logger.error(f"❌ Login failed! URL: {driver.current_url}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        return False

def is_browser_alive() -> bool:
    try:
        driver.current_url
        return True
    except:
        return False

def check_session_valid() -> bool:
    try:
        driver.find_element(By.CSS_SELECTOR, "table tbody")
        return True
    except:
        return False

# ========== SMS DETECTION (NO PAGE REFRESH) ==========
def get_otp_from_page() -> Optional[Dict]:
    """Get OTP using JavaScript - NO PAGE REFRESH"""
    global driver
    
    try:
        # JavaScript to read SMS table without refresh
        script = """
        var result = null;
        var table = document.querySelector('table tbody');
        if (table) {
            var rows = table.querySelectorAll('tr');
            for (var i = 0; i < Math.min(rows.length, 5); i++) {
                var cells = rows[i].querySelectorAll('td');
                if (cells.length >= 2) {
                    var rowText = rows[i].innerText;
                    if (rowText && rowText.length > 10 && !rowText.includes('SID')) {
                        var phone = cells[0] ? cells[0].innerText.trim() : '';
                        var message = cells[cells.length-1] ? cells[cells.length-1].innerText.trim() : '';
                        if (message.length > 5) {
                            result = { phone: phone, message: message };
                            break;
                        }
                    }
                }
            }
        }
        return result;
        """
        
        sms = driver.execute_script(script)
        
        if not sms:
            return None
        
        message = sms.get('message', '')
        phone = sms.get('phone', 'Unknown')
        
        if not message or len(message) < 5:
            return None
        
        otp = extract_otp(message)
        
        if otp:
            return {
                "otp": otp,
                "phone": phone,
                "message": message,
                "service": get_service(message),
                "country": get_country_from_phone(phone)
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting OTP: {e}")
        return None

# ========== TELEGRAM MESSAGING ==========
def format_otp_message(otp_data: Dict) -> str:
    otp = otp_data['otp']
    if len(otp) == 6:
        formatted_otp = f"{otp[:3]} {otp[3:]}"
    elif len(otp) == 5:
        formatted_otp = f"{otp[:2]} {otp[2:]}"
    else:
        formatted_otp = otp
    
    phone_display = otp_data['phone'][-6:] if len(otp_data['phone']) > 6 else otp_data['phone']
    
    return f"""
{otp_data['country']}

🔐 <b>OTP:</b> <code>{formatted_otp}</code>

🌐 <b>Service:</b> {otp_data['service']}
📱 <b>From:</b> {phone_display}
⏰ <b>Time:</b> {datetime.now().strftime('%I:%M:%S %p')}

<i>👆 Tap OTP to copy</i>
""".strip()

async def send_telegram_message(app, text: str) -> bool:
    """Send message with retry"""
    for attempt in range(MAX_RETRIES):
        try:
            async with telegram_semaphore:
                await app.bot.send_message(
                    chat_id=CHAT_ID,
                    text=text,
                    parse_mode="HTML"
                )
                await asyncio.sleep(0.5)
                return True
        except Exception as e:
            logger.error(f"Send attempt {attempt+1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2 ** attempt)
    return False

async def send_otp_to_telegram(app, otp_data: Dict) -> bool:
    """Send OTP - NO DUPLICATE"""
    global sent_otps
    
    async with sent_otps_lock:
        otp_key = f"{otp_data['otp']}_{otp_data['phone']}"
        
        if otp_key in sent_otps:
            logger.info(f"⏭️ Duplicate skipped: {otp_data['otp']}")
            return False
        
        message = format_otp_message(otp_data)
        
        if await send_telegram_message(app, message):
            sent_otps[otp_key] = datetime.now().isoformat()
            save_sent_otps()
            logger.info(f"✅ SENT: {otp_data['otp']} - {otp_data['service']}")
            return True
        
        return False

# ========== TELEGRAM COMMANDS ==========
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ <b>OTP Bot Active!</b>\n\n"
        "📱 Status: Monitoring\n"
        "🔄 No duplicate OTP\n"
        "🌍 Auto country detection\n"
        "🐌 Slow typing: ENABLED\n"
        f"⏰ Uptime: {int(time.time() - bot_start_time)}s",
        parse_mode="HTML"
    )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    await update.message.reply_text(
        f"<b>📊 Bot Status</b>\n\n"
        f"Status: {'🟢 Active' if driver and is_browser_alive() else '🔴 Stopped'}\n"
        f"OTP Sent: {len(sent_otps)}\n"
        f"Uptime: {int(time.time() - bot_start_time)}s\n"
        f"Slow Typing: ON",
        parse_mode="HTML"
    )

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global sent_otps
    
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    async with sent_otps_lock:
        sent_otps.clear()
        save_sent_otps()
    
    await update.message.reply_text("✅ Reset complete! All OTPs will be resent.", parse_mode="HTML")

async def test_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    await update.message.reply_text("🔍 Checking for OTP...", parse_mode="HTML")
    
    otp_data = get_otp_from_page()
    if otp_data:
        await send_otp_to_telegram(app, otp_data)
        await update.message.reply_text(f"✅ OTP {otp_data['otp']} sent!", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ No new OTP found", parse_mode="HTML")

# ========== MAIN MONITOR LOOP ==========
async def monitor_sms(app):
    global driver, last_refresh_time
    
    logger.info("🚀 Starting OTP Monitor...")
    logger.info("🐌 Slow typing mode ENABLED")
    load_sent_otps()
    
    # Initialize browser
    if not init_browser():
        logger.error("❌ Browser failed")
        await send_telegram_message(app, "❌ Bot failed to start")
        return
    
    # Login with slow typing
    if not login():
        logger.error("❌ Login failed")
        await send_telegram_message(app, "❌ Login failed! Check credentials")
        return
    
    # Go to SMS page (ONCE - no auto refresh)
    logger.info("📱 Loading SMS page...")
    driver.get("https://www.ivasms.com/portal/live/my_sms")
    time.sleep(5)
    
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody"))
        )
        logger.info("✅ SMS page loaded - NO AUTO REFRESH")
    except:
        logger.warning("Table not found, but continuing...")
    
    last_refresh_time = time.time()
    
    await send_telegram_message(app, "✅ Bot started! Monitoring OTPs...")
    
    error_count = 0
    
    while True:
        try:
            # Periodic page refresh (every 30 seconds)
            if time.time() - last_refresh_time > PAGE_REFRESH_INTERVAL:
                logger.info("🔄 Refreshing page...")
                driver.refresh()
                time.sleep(3)
                last_refresh_time = time.time()
            
            # Check session
            if not check_session_valid():
                logger.warning("Session expired, re-logging...")
                if not login():
                    await asyncio.sleep(10)
                    continue
            
            # Get OTP
            otp_data = get_otp_from_page()
            
            if otp_data:
                await send_otp_to_telegram(app, otp_data)
                error_count = 0
            
            await asyncio.sleep(CHECK_INTERVAL)
            
        except WebDriverException as e:
            logger.error(f"WebDriver error: {e}")
            error_count += 1
            
            if error_count >= 3:
                logger.warning("Restarting browser...")
                try:
                    driver.quit()
                except:
                    pass
                
                if init_browser() and login():
                    driver.get("https://www.ivasms.com/portal/live/my_sms")
                    time.sleep(5)
                    error_count = 0
                    last_refresh_time = time.time()
                else:
                    await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            error_count += 1
            await asyncio.sleep(5)

async def post_init(app):
    asyncio.create_task(monitor_sms(app))

# ========== MAIN ==========
def main():
    global app
    try:
        print("\n" + "="*55)
        print("   🔥 IVASMS OTP FORWARDING BOT 🔥")
        print("   FINAL VERSION - SLOW TYPING ENABLED")
        print("   Powered by EUW IT GROUP")
        print("="*55 + "\n")
        
        app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
        app.add_handler(CommandHandler("start", start_cmd))
        app.add_handler(CommandHandler("status", status_cmd))
        app.add_handler(CommandHandler("reset", reset_cmd))
        app.add_handler(CommandHandler("test", test_cmd))
        
        logger.info("🤖 Bot is running...")
        logger.info("🐌 Slow typing mode ENABLED (0.15-0.35s per character)")
        logger.info("⚡ Checking every 5 seconds")
        logger.info("🔄 Page refreshes every 30 seconds")
        
        app.run_polling()
        
    except KeyboardInterrupt:
        logger.info("⏹️ Bot stopped")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()

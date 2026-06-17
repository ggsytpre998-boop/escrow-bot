import telebot
import random
import string
import re
import logging
import os
from flask import Flask
import threading

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Render ke liye Dummy Web Server
app = Flask('')

@app.route('/')
def home():
    return "Elite Escrow Bot is Online!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Token Render ke dashboard se secure tarike se aayega
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

active_deals = {}

def clean_fancy_text(text):
    if not text: return ""
    fancy_map = {
        'ʙ': 'b', 'ᴜ': 'u', 'ʏ': 'y', 'ᴇ': 'e', 'ʀ': 'r',
        '|': '', 'ai': '', '🔥': '', '👑': '', '⚠️': '', '🍁': '', '🤝': '',
        '<b>': '', '</b>': '', '<i>': '', '</i>': '',
        'ꜱ': 's', 'ʟ': 'l', 'ᴅ': 'd', 'ᴀ': 'a', 'ᴍ': 'm',
        'ᴏ': 'o', '½': 'n', 'ᴛ': 't', 'ꜰ': 'f', 'ᴘ': 'p',
        'ɢ': 'g', 'ʜ': 'h', 'ɪ': 'i', 'ᴊ': 'j', 'ᴋ': 'k',
        'ᴠ': 'v', 'ᴡ': 'w', 'x': 'x', 'ᴢ': 'z', '🇨': 'c', 'ɴ': 'n'
    }
    text_lower = text.lower()
    return "".join([fancy_map.get(char, char) for char in text_lower])

def format_amount(amount):
    if amount == int(amount): return str(int(amount))
    return f"{amount:.2f}"

def is_admin(chat_id, user_id):
    try:
        chat_member = bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ['administrator', 'creator']
    except Exception: return False

def calculate_charges(amount):
    if amount <= 100: return 5
    elif amount <= 300: return 10
    elif amount <= 500: return 20
    elif amount <= 1000: return 30
    elif amount <= 2000: return 40
    elif amount <= 3000: return 50
    elif amount <= 4000: return 70
    else: return amount * 0.035

def generate_trade_id():
    chars = string.ascii_uppercase + string.digits
    return "#TID" + ''.join(random.choices(chars, k=6))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 💰 COMMANDS & LISTENERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=['charges'])
def check_charges(message):
    if not is_admin(message.chat.id, message.from_user.id): return 
    try:
        amount = float(message.text.split()[1])
        fee = calculate_charges(amount)
        bot.reply_to(message, f"₹{format_amount(fee)}")
    except: pass

@bot.message_handler(commands=['add'])
def add_deal(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: return
    try:
        received_amount = float(message.text.split()[1])
        raw_text = message.reply_to_message.text or ""
        decoded_text = clean_fancy_text(raw_text)
        
        # 🔥 UPDATED REGEX: Ab 'buyer tag' ya sirf 'buyer' dono ko dhoond nikalega
        buyer_match = re.search(r'buyer\s*(?:tag)?\s*[:\-=\s]*\s*(@\w+)', decoded_text)
        seller_match = re.search(r'seller\s*(?:tag)?\s*[:\-=\s]*\s*(@\w+)', decoded_text)
        deal_amt_match = re.search(r'(?:deal\s*)?amount\s*[:\-=\s]*\s*(?:₹\s*)?([\d,]+(?:\.\d+)?)', decoded_text)

        buyer_username = buyer_match.group(1) if buyer_match else "Not Found"
        seller_username = seller_match.group(1) if seller_match else "Not Found"
        
        if deal_amt_match: deal_amount = float(deal_amt_match.group(1).replace(',', ''))
        else: deal_amount = received_amount

        fee = calculate_charges(deal_amount)
        release_amount = received_amount - fee
        trade_id = generate_trade_id()
        escrow_admin = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name

        active_deals[trade_id] = {"buyer": buyer_username, "seller": seller_username, "received": received_amount, "release": release_amount, "admin": escrow_admin}

        text = f"""🤝 <b>Continue the Deal</b>

💰 <b>Deal amount:</b> ₹{format_amount(deal_amount)}
🔴 <b>received Amount:</b> ₹{format_amount(received_amount)}
🔵 <b>Release/Refund amount:</b> ₹{format_amount(release_amount)}
🆔 <b>Trade id:</b> <code>{trade_id}</code>
🪪 <b>Buyer:</b> {buyer_username}
🪪 <b>Seller:</b> {seller_username}
🖲️ <b>Escrowed by:</b> {escrow_admin}

🛡️ <b>DEAL SECURED</b> 🛡️"""
        bot.reply_to(message, text)
    except Exception as e:
        bot.reply_to(message, "⚠️ Error! Amount sahi se daalein.")

@bot.message_handler(commands=['release'])
def release_deal(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    try:
        trade_id = message.text.split()[1].upper()
        if trade_id not in active_deals:
            bot.reply_to(message, "⚠️ Invalid Trade ID.")
            return

        deal = active_deals[trade_id]
        text = f"""🔴 <b>Deal completed</b>

🆔 <b>Trade id:</b> <code>{trade_id}</code>
🔴 <b>received Amount:</b> ₹{format_amount(deal['received'])}
🔵 <b>Released successful:</b> ₹{format_amount(deal['release'])}

🪪 <b>Buyer:</b> {deal['buyer']}
🪪 <b>Seller:</b> {deal['seller']}

<i>{deal['buyer']} and {deal['seller']} are requested to drop the vouch before leaving👇🏻</i>

<code>Vouch Elite dva escrow ₹{format_amount(deal['release'])} smooth escrow deal ✅</code>

🖲️ <b>Escrowed by:</b> {deal['admin']}

🛡️ <b>DEAL SECURED</b> 🛡️"""
        bot.reply_to(message, text)
        del active_deals[trade_id]
    except:
        bot.reply_to(message, "Sahi format: <code>/release #TIDXXXXXX</code>")

@bot.message_handler(commands=['refund'])
def refund_deal(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    try:
        trade_id = message.text.split()[1].upper()
        if trade_id not in active_deals:
            bot.reply_to(message, "⚠️ Invalid Trade ID.")
            return

        deal = active_deals[trade_id]
        text = f"""❌ <b>Deal Cancelled & Refunded</b>

🆔 <b>Trade id:</b> <code>{trade_id}</code>
🔴 <b>Received Amount:</b> ₹{format_amount(deal['received'])}
↩️ <b>Refunded Amount:</b> ₹{format_amount(deal['release'])}

🪪 <b>Buyer:</b> {deal['buyer']}
🪪 <b>Seller:</b> {deal['seller']}

💸 <i>Refund complete. Amount returned successfully to the buyer.</i>

🖲️ <b>Escrowed by:</b> {deal['admin']}

🛡️ <b>DEAL SECURED</b> 🛡️"""
        bot.reply_to(message, text)
        del active_deals[trade_id]
    except:
        bot.reply_to(message, "Sahi format: <code>/refund #TIDXXXXXX</code>")

@bot.message_handler(func=lambda message: message.text and not message.text.startswith('/') and not message.text.startswith('!'))
def global_text_handler(message):
    cleaned = clean_fancy_text(message.text)
    if "amount" in cleaned or "deal" in cleaned:
        try:
            deal_amt_match = re.search(r'(?:deal\s*)?amount\s*[:\-=\s]*\s*(?:₹\s*)?([\d,]+(?:\.\d+)?)', cleaned)
            if deal_amt_match:
                deal_amount = float(deal_amt_match.group(1).replace(',', ''))
                fee = calculate_charges(deal_amount)
                
                reply_text = f"""🍁 <b>Escrow Charges Calculator</b>

💰 <b>Deal Amount:</b> ₹{format_amount(deal_amount)}
💵 <b>Escrow Fee:</b> ₹{format_amount(fee)}

⚠️ <i><b>T&C:</b> If a Deal is Cancelled, 100% of Charges Will Be Deducted.</i>"""
                bot.reply_to(message, reply_text)
        except: pass

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_web_server)
    server_thread.start()
    
    print("Elite Escrow Bot is running perfectly...")
    bot.infinity_polling()
                                          

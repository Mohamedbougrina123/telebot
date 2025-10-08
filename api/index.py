from flask import Flask, request, jsonify
import requests
import re
import threading
import asyncio
from telethon import TelegramClient
from telethon.tl.types import InputPeerUser

app = Flask(__name__)

BOT_TOKEN = "8328267645:AAEgq7skSPifXizqPriMkiUt4oDPPm-I5R8"
API_ID = 29520252
API_HASH = '55a15121bb420b21c3f9e8ccabf964cf'

class TelegramAuth:
    def __init__(self):
        self.client = None
        self.auth_ready = False
        self.phone_number = None
        self.code_required = False

    async def connect(self):
        self.client = TelegramClient('bougrina', API_ID, API_HASH)
        await self.client.connect()
        return await self.client.is_user_authorized()

    async def send_code_request(self, phone_number):
        self.phone_number = phone_number
        await self.client.send_code_request(phone_number)
        self.code_required = True
        return True

    async def sign_in(self, code):
        if not self.code_required:
            return False, "لم يتم طلب الرمز بعد"
        
        try:
            await self.client.sign_in(self.phone_number, code)
            self.auth_ready = True
            self.code_required = False
            return True, "تم تسجيل الدخول بنجاح"
        except Exception as e:
            return False, f"خطأ في تسجيل الدخول: {str(e)}"

    async def send_message(self, text):
        if not self.auth_ready:
            return False, "لم يتم تسجيل الدخول بعد"
        try:
            await self.client.send_message('@fakemailbot', text)
            return True, "تم إرسال الرسالة"
        except Exception as e:
            return False, f"خطأ في إرسال الرسالة: {str(e)}"

    def disconnect(self):
        if self.client:
            asyncio.run(self.client.disconnect())

telegram_auth = TelegramAuth()

class BotManager:
    def __init__(self):
        self.running = False
        self.loop_count = 0
        self.current_email = ""

    def start_bot(self, email):
        self.running = True
        self.loop_count = 0
        self.current_email = email

        async def run_async():
            while self.running:
                try:
                    success, message = await telegram_auth.send_message(email)
                    if success:
                        self.loop_count += 1
                        print(f"Sent: {email} - Count: {self.loop_count}")
                    else:
                        print(f"Failed to send: {message}")
                    await asyncio.sleep(3)
                except Exception as e:
                    print(f"Loop error: {e}")
                    await asyncio.sleep(1)

        def start_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run_async())
            except Exception as e:
                print(f"Async loop error: {e}")
            finally:
                loop.close()

        thread = threading.Thread(target=start_loop)
        thread.daemon = True
        thread.start()

    def stop_bot(self):
        self.running = False

bot_manager = BotManager()

@app.route('/')
def home():
    return "Telegram Bot is Running!"

@app.route('/api/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Webhook is active and ready!"

    try:
        data = request.get_json()

        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            text = message.get('text', '').strip()

            if text.startswith('/start'):
                handle_start(chat_id, text)
            elif text.startswith('/auth_phone'):
                handle_auth_phone(chat_id, text)
            elif text.startswith('/auth_code'):
                handle_auth_code(chat_id, text)
            elif text == '/stop':
                handle_stop(chat_id)
            elif text == '/status':
                handle_status(chat_id)
            elif text == '/help':
                handle_help(chat_id)
            else:
                send_message(chat_id, "Unknown command")

    except Exception as e:
        print(f"Webhook error: {e}")

    return jsonify({"status": "success"})

def handle_auth_phone(chat_id, text):
    parts = text.split()
    if len(parts) < 2:
        send_message(chat_id, "Usage: /auth_phone +212612345678")
        return
    
    phone = parts[1]
    
    async def auth_phone():
        connected = await telegram_auth.connect()
        if not connected:
            success = await telegram_auth.send_code_request(phone)
            if success:
                send_message(chat_id, f"تم إرسال رمز التحقق إلى {phone}. أرسل الرمز باستخدام /auth_code الرمز")
            else:
                send_message(chat_id, "فشل في إرسال رمز التحقق")
        else:
            send_message(chat_id, "تم تسجيل الدخول مسبقاً")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(auth_phone())
    loop.close()

def handle_auth_code(chat_id, text):
    parts = text.split()
    if len(parts) < 2:
        send_message(chat_id, "Usage: /auth_code 12345")
        return
    
    code = parts[1]

    async def auth_code():
        success, message = await telegram_auth.sign_in(code)
        send_message(chat_id, message)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(auth_code())
    loop.close()

def handle_start(chat_id, text):
    if not telegram_auth.auth_ready:
        send_message(chat_id, "يجب تسجيل الدخول أولاً باستخدام:\n1. /auth_phone +212612345678\n2. /auth_code 12345")
        return

    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)

    if not email_match:
        send_message(chat_id, "Usage: /start email@gmail.com")
        return

    email = email_match.group()

    if bot_manager.running:
        send_message(chat_id, f"Bot already running with: {bot_manager.current_email}")
        return

    bot_manager.start_bot(email)
    send_message(chat_id, f"Started with: {email}\nBot is now sending messages to @fakemailbot")

def handle_stop(chat_id):
    if not bot_manager.running:
        send_message(chat_id, "Bot not running")
        return

    bot_manager.stop_bot()
    send_message(chat_id, f"Stopped - Total messages sent: {bot_manager.loop_count}")

def handle_status(chat_id):
    auth_status = "مصادق" if telegram_auth.auth_ready else "غير مصادق"
    bot_status = "شغال" if bot_manager.running else "متوقف"
    email_info = f" مع: {bot_manager.current_email}" if bot_manager.running else ""
    message = f"الحالة:\nالمصادقة: {auth_status}\nالبوت: {bot_status}{email_info}\nعدد الرسائل: {bot_manager.loop_count}"
    send_message(chat_id, message)

def handle_help(chat_id):
    help_text = """
أوامر البوت:

1. المصادقة:
/auth_phone +212612345678 - إرسال رمز التحقق
/auth_code 12345 - إدخال رمز التحقق

2. البوت:
/start email@gmail.com - بدء إرسال الإيميل
/stop - إيقاف البوت
/status - حالة البوت
/help - المساعدة

مثال:
/auth_phone +212612345678
/auth_code 12345
/start test@gmail.com
"""
    send_message(chat_id, help_text)

def send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Message sent to {chat_id}: {response.status_code}")
    except Exception as e:
        print(f"Error sending message: {e}")

if __name__ == '__main__':
    app.run(debug=True)

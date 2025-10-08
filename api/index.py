from flask import Flask, request, jsonify
import requests
import re
import threading
import asyncio
from telethon import TelegramClient
from telethon.tl.types import InputPhoneContact
from telethon.tl.functions.contacts import ImportContactsRequest

app = Flask(__name__)

BOT_TOKEN = "8328267645:AAEgq7skSPifXizqPriMkiUt4oDPPm-I5R8"
API_ID = 22154260
API_HASH = '6bae7de9fdd9031aede658ec8a8b57c0'

class TelegramAuth:
    def __init__(self):
        self.client = None
        self.auth_ready = False
        self.phone_number = None
        self.code_required = False
        self.user_states = {}
        self.phone_hash = {}

    async def connect_phone(self, phone_number):
        try:
            self.client = TelegramClient('session_name', API_ID, API_HASH)
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                result = await self.client.send_code_request(phone_number)
                self.phone_hash[phone_number] = result.phone_code_hash
                self.phone_number = phone_number
                self.code_required = True
                return True, "تم إرسال الرمز"
            else:
                self.auth_ready = True
                return True, "تم تسجيل الدخول مسبقاً"
                
        except Exception as e:
            return False, f"خطأ: {str(e)}"

    async def sign_in_with_code(self, phone_number, code):
        try:
            if phone_number in self.phone_hash:
                await self.client.sign_in(
                    phone=phone_number,
                    code=code,
                    phone_code_hash=self.phone_hash[phone_number]
                )
                self.auth_ready = True
                self.code_required = False
                return True, "تم تسجيل الدخول بنجاح"
            else:
                return False, "لم يتم طلب رمز لهذا الرقم"
        except Exception as e:
            return False, f"خطأ في تسجيل الدخول: {str(e)}"

    async def send_message(self, text):
        try:
            await self.client.send_message('@fakemailbot', text)
            return True, "تم إرسال الرسالة"
        except Exception as e:
            return False, f"خطأ في إرسال الرسالة: {str(e)}"

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
                    await asyncio.sleep(3)
                except Exception as e:
                    await asyncio.sleep(1)

        def start_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_async())
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

@app.route('/api/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            text = message.get('text', '').strip()

            if chat_id not in telegram_auth.user_states:
                telegram_auth.user_states[chat_id] = 'start'

            state = telegram_auth.user_states[chat_id]

            if text == '/start':
                telegram_auth.user_states[chat_id] = 'awaiting_phone'
                send_message(chat_id, "📞 Please enter your phone number (e.g., +212612345678):")
            
            elif state == 'awaiting_phone':
                if text.startswith('+'):
                    async def handle_phone():
                        success, message = await telegram_auth.connect_phone(text)
                        if success:
                            telegram_auth.user_states[chat_id] = 'awaiting_code'
                            send_message(chat_id, f"✅ {message}\n🔢 Please enter the code you received:")
                        else:
                            send_message(chat_id, f"❌ {message}")
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(handle_phone())
                    loop.close()
                else:
                    send_message(chat_id, "❌ Invalid phone number. Must start with +")

            elif state == 'awaiting_code':
                async def handle_code():
                    success, message = await telegram_auth.sign_in_with_code(telegram_auth.phone_number, text)
                    if success:
                        telegram_auth.user_states[chat_id] = 'authenticated'
                        send_message(chat_id, f"✅ {message}\n📧 Now send: /start_email your_email@gmail.com")
                    else:
                        send_message(chat_id, f"❌ {message}")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(handle_code())
                loop.close()

            elif text.startswith('/start_email'):
                if telegram_auth.auth_ready:
                    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
                    if email_match:
                        email = email_match.group()
                        if not bot_manager.running:
                            bot_manager.start_bot(email)
                            send_message(chat_id, f"✅ Started sending: {email}")
                        else:
                            send_message(chat_id, f"⚠️ Bot already running with: {bot_manager.current_email}")
                    else:
                        send_message(chat_id, "❌ Usage: /start_email your_email@gmail.com")
                else:
                    send_message(chat_id, "❌ Please authenticate first with /start")

            elif text == '/stop':
                if bot_manager.running:
                    bot_manager.stop_bot()
                    send_message(chat_id, f"⏹️ Stopped - Messages sent: {bot_manager.loop_count}")
                else:
                    send_message(chat_id, "❌ Bot is not running")

            elif text == '/status':
                auth_status = "✅ Authenticated" if telegram_auth.auth_ready else "❌ Not authenticated"
                bot_status = "🟢 Running" if bot_manager.running else "🔴 Stopped"
                email_info = f" - Email: {bot_manager.current_email}" if bot_manager.running else ""
                message = f"📊 Status:\n{auth_status}\n{bot_status}{email_info}\n📨 Messages: {bot_manager.loop_count}"
                send_message(chat_id, message)

            elif text == '/help':
                help_text = """
🤖 Bot Commands:

/start - Start authentication process
/start_email email@example.com - Start sending emails
/stop - Stop bot
/status - Check status
/help - Show this help

Authentication steps:
1. Send /start
2. Enter your phone (e.g., +212612345678)
3. Enter the code you receive
"""
                send_message(chat_id, help_text)

    except Exception as e:
        print(f"Webhook error: {e}")

    return jsonify({"status": "success"})

def send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error sending message: {e}")

if __name__ == '__main__':
    app.run(debug=True)

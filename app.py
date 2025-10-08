from flask import Flask, request, jsonify
import requests
import re
import threading
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
import os
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN', "8328267645:AAEgq7skSPifXizqPriMkiUt4oDPPm-I5R8")
API_ID = int(os.environ.get('API_ID', 22154260))
API_HASH = os.environ.get('API_HASH', '6bae7de9fdd9031aede658ec8a8b57c0')
PORT = int(os.environ.get('PORT', 10000))

class TelegramAuth:
    def __init__(self):
        self.client = None
        self.auth_ready = False
        self.phone_number = None
        self.user_states = {}
        self.phone_hash = {}
        self.session_strings = {}
        self.lock = asyncio.Lock()

    async def connect_phone(self, phone_number, chat_id):
        try:
            async with self.lock:
                session = StringSession()
                self.client = TelegramClient(session, API_ID, API_HASH)
                await self.client.connect()
                
                if not await self.client.is_user_authorized():
                    result = await self.client.send_code_request(phone_number)
                    self.phone_hash[chat_id] = {
                        'phone': phone_number,
                        'hash': result.phone_code_hash,
                        'session': session
                    }
                    self.phone_number = phone_number
                    return True, "تم إرسال الرمز"
                else:
                    self.auth_ready = True
                    self.session_strings[chat_id] = session.save()
                    return True, "تم تسجيل الدخول مسبقاً"
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False, f"خطأ: {str(e)}"

    async def sign_in_with_code(self, chat_id, code):
        try:
            async with self.lock:
                if chat_id in self.phone_hash:
                    phone_data = self.phone_hash[chat_id]
                    
                    try:
                        await self.client.sign_in(
                            phone=phone_data['phone'],
                            code=code,
                            phone_code_hash=phone_data['hash']
                        )
                        
                        self.auth_ready = True
                        self.session_strings[chat_id] = phone_data['session'].save()
                        del self.phone_hash[chat_id]
                        return True, "تم تسجيل الدخول بنجاح"
                        
                    except Exception as sign_in_error:
                        if "expired" in str(sign_in_error):
                            result = await self.client.send_code_request(phone_data['phone'])
                            self.phone_hash[chat_id]['hash'] = result.phone_code_hash
                            return False, "انتهت صلاحية الرمز. تم إرسال رمز جديد، أرسل الرمز الجديد:"
                        else:
                            return False, f"خطأ في تسجيل الدخول: {str(sign_in_error)}"
                else:
                    return False, "لم يتم طلب رمز لهذا الرقم"
        except Exception as e:
            logger.error(f"Sign in error: {e}")
            return False, f"خطأ: {str(e)}"

    async def restore_session(self, chat_id):
        try:
            async with self.lock:
                if chat_id in self.session_strings:
                    session = StringSession(self.session_strings[chat_id])
                    self.client = TelegramClient(session, API_ID, API_HASH)
                    await self.client.connect()
                    
                    if await self.client.is_user_authorized():
                        self.auth_ready = True
                        return True
                return False
        except Exception as e:
            logger.error(f"Restore session error: {e}")
            return False

    async def send_message(self, text):
        try:
            async with self.lock:
                if self.client and self.client.is_connected():
                    await self.client.send_message('@fakemailbot', text)
                    return True
                else:
                    # إعادة الاتصال إذا كان مفصولاً
                    if self.client:
                        await self.client.connect()
                        if await self.client.is_user_authorized():
                            await self.client.send_message('@fakemailbot', text)
                            return True
                    return False
        except Exception as e:
            logger.error(f"Send message error: {e}")
            return False

telegram_auth = TelegramAuth()

class BotManager:
    def __init__(self):
        self.running = False
        self.loop_count = 0
        self.current_email = ""
        self.thread = None
        self.stop_event = threading.Event()

    def start_bot(self, email, chat_id):
        if self.running:
            return False
            
        self.running = True
        self.loop_count = 0
        self.current_email = email
        self.stop_event.clear()

        def run_bot():
            async def main():
                try:
                    await telegram_auth.restore_session(chat_id)
                    
                    while self.running and not self.stop_event.is_set():
                        try:
                            success = await telegram_auth.send_message(email)
                            if success:
                                self.loop_count += 1
                                logger.info(f"Message sent: {self.loop_count}")
                            await asyncio.sleep(1)  # زيادة الوقت لتجنب الحظر
                        except Exception as e:
                            logger.error(f"Bot loop error: {e}")
                            await asyncio.sleep(2)
                            continue
                except Exception as e:
                    logger.error(f"Bot main error: {e}")

            # إنشاء loop جديد لكل thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(main())
            finally:
                loop.close()

        self.thread = threading.Thread(target=run_bot)
        self.thread.daemon = True
        self.thread.start()
        return True

    def stop_bot(self):
        self.running = False
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)

bot_manager = BotManager()

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "message": "Telegram Bot is Running 24/7!",
        "bot_status": "running" if bot_manager.running else "stopped",
        "loop_count": bot_manager.loop_count
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/api/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400
        
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            text = message.get('text', '').strip()

            if chat_id not in telegram_auth.user_states:
                telegram_auth.user_states[chat_id] = 'start'

            state = telegram_auth.user_states[chat_id]

            if text == '/start':
                telegram_auth.user_states[chat_id] = 'awaiting_phone'
                send_message(chat_id, "Please enter your phone number (with country code):")
            
            elif state == 'awaiting_phone':
                if text.startswith('+'):
                    # تشغيل async function في thread منفصل
                    def run_connect():
                        return asyncio.run(telegram_auth.connect_phone(text, chat_id))
                    
                    result = run_connect()
                    if result[0]:
                        telegram_auth.user_states[chat_id] = 'awaiting_code'
                        send_message(chat_id, "Please enter the code you received:")
                    else:
                        send_message(chat_id, result[1])
                else:
                    send_message(chat_id, "رقم الهاتف غير صحيح. يرجى استخدام الصيغة: +1234567890")

            elif state == 'awaiting_code':
                def run_sign_in():
                    return asyncio.run(telegram_auth.sign_in_with_code(chat_id, text))
                
                result = run_sign_in()
                if result[0]:
                    telegram_auth.user_states[chat_id] = 'authenticated'
                    send_message(chat_id, "تم تسجيل الدخول بنجاح! أرسل /start_email your_email@gmail.com")
                else:
                    send_message(chat_id, result[1])

            elif text.startswith('/start_email'):
                if telegram_auth.auth_ready:
                    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
                    if email_match:
                        email = email_match.group()
                        if bot_manager.start_bot(email, chat_id):
                            send_message(chat_id, f"بدأ الإرسال باستخدام: {email}\n⚡ يعمل 24/7")
                        else:
                            send_message(chat_id, "البوت يعمل بالفعل")
                    else:
                        send_message(chat_id, "استخدم: /start_email your_email@gmail.com")
                else:
                    send_message(chat_id, "يجب تسجيل الدخول أولاً. أرسل /start")

            elif text == '/stop':
                if bot_manager.running:
                    bot_manager.stop_bot()
                    send_message(chat_id, f"تم الإيقاف - عدد الرسائل: {bot_manager.loop_count}")
                else:
                    send_message(chat_id, "البوت غير شغال")

            elif text == '/status':
                auth_status = "مصادق" if telegram_auth.auth_ready else "غير مصادق"
                bot_status = "شغال" if bot_manager.running else "متوقف"
                email_info = f" - {bot_manager.current_email}" if bot_manager.running else ""
                message = f"المصادقة: {auth_status}\nالبوت: {bot_status}{email_info}\nالرسائل: {bot_manager.loop_count}"
                send_message(chat_id, message)

            elif text == '/help':
                help_text = """
/start - بدء المصادقة
/start_email email - بدء الإرسال 24/7
/stop - إيقاف البوت
/status - الحالة
/help - المساعدة
                """
                send_message(chat_id, help_text.strip())

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "success"})

def send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            logger.error(f"Telegram API error: {response.text}")
    except Exception as e:
        logger.error(f"Send message error: {e}")

@app.route('/test')
def test():
    return jsonify({"message": "Test endpoint working"})

# هذا مهم لـ Render
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)

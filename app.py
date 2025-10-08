from flask import Flask, request, jsonify
import requests
import re
import asyncio
import threading
from telethon import TelegramClient
from telethon.sessions import StringSession
import os
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# المتغيرات البيئية
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8328267645:AAEgq7skSPifXizqPriMkiUt4oDPPm-I5R8")
API_ID = int(os.environ.get('API_ID', 22154260))
API_HASH = os.environ.get('API_HASH', '6bae7de9fdd9031aede658ec8a8b57c0')
PORT = int(os.environ.get('PORT', 10000))

class TelegramManager:
    def __init__(self):
        self.user_sessions = {}
        self.user_states = {}
        
    async def send_code_request(self, phone_number, chat_id):
        """إرسال طلب الرمز"""
        try:
            session = StringSession()
            client = TelegramClient(session, API_ID, API_HASH)
            
            await client.connect()
            
            # إرسال الرمز
            result = await client.send_code_request(phone_number)
            
            # حفظ البيانات
            self.user_sessions[chat_id] = {
                'client': client,
                'phone_number': phone_number,
                'phone_code_hash': result.phone_code_hash,
                'session': session
            }
            
            return True, "✅ تم إرسال الرمز إلى رقمك"
            
        except Exception as e:
            logger.error(f"Error sending code: {e}")
            return False, f"❌ خطأ في إرسال الرمز: {str(e)}"
    
    async def sign_in(self, chat_id, code):
        """تسجيل الدخول بالرمز"""
        try:
            if chat_id not in self.user_sessions:
                return False, "❌ لم يتم طلب رمز لهذا الرقم"
            
            user_data = self.user_sessions[chat_id]
            client = user_data['client']
            
            # تسجيل الدخول
            await client.sign_in(
                phone=user_data['phone_number'],
                code=code,
                phone_code_hash=user_data['phone_code_hash']
            )
            
            # حفظ الجلسة
            session_string = user_data['session'].save()
            self.user_sessions[chat_id]['session_string'] = session_string
            self.user_states[chat_id] = 'authenticated'
            
            return True, "✅ تم تسجيل الدخول بنجاح!"
            
        except Exception as e:
            logger.error(f"Error signing in: {e}")
            return False, f"❌ خطأ في تسجيل الدخول: {str(e)}"
    
    async def send_message(self, chat_id, text):
        """إرسال رسالة"""
        try:
            if chat_id not in self.user_sessions:
                return False
            
            client = self.user_sessions[chat_id]['client']
            
            if await client.is_user_authorized():
                await client.send_message('@fakemailbot', text)
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

# إنشاء المدير
telegram_manager = TelegramManager()

class BotRunner:
    def __init__(self):
        self.running = False
        self.message_count = 0
        self.current_email = ""
        self.thread = None
    
    def start(self, email, chat_id):
        """بدء البوت"""
        if self.running:
            return False
            
        self.running = True
        self.message_count = 0
        self.current_email = email
        
        def run_loop():
            async def main():
                while self.running:
                    try:
                        success = await telegram_manager.send_message(chat_id, email)
                        if success:
                            self.message_count += 1
                            logger.info(f"📨 تم إرسال الرسالة #{self.message_count}")
                        await asyncio.sleep(2)  # انتظار 2 ثانية بين الرسائل
                    except Exception as e:
                        logger.error(f"Bot error: {e}")
                        await asyncio.sleep(5)
            
            # إنشاء loop جديد
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(main())
            finally:
                loop.close()
        
        self.thread = threading.Thread(target=run_loop)
        self.thread.daemon = True
        self.thread.start()
        return True
    
    def stop(self):
        """إيقاف البوت"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

bot_runner = BotRunner()

# دوال المساعدة
def send_telegram_message(chat_id, text):
    """إرسال رسالة عبر بوت التلغرام"""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Telegram API error: {e}")
        return False

def run_async(coroutine):
    """تشغيل دالة async في thread منفصل"""
    def wrapper():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coroutine)
        finally:
            loop.close()
    
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(wrapper)
        return future.result()

# Routes
@app.route('/')
def home():
    return "🤖 البوت يعمل بشكل طبيعي!"

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "bot_running": bot_runner.running})

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """webhook لاستقبال الرسائل من التلغرام"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data"}), 400
        
        message = data.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '').strip()
        
        if not chat_id:
            return jsonify({"status": "error", "message": "No chat ID"}), 400
        
        logger.info(f"📩 Received: {text} from {chat_id}")
        
        # معالجة الأوامر
        if text == '/start':
            telegram_manager.user_states[chat_id] = 'awaiting_phone'
            send_telegram_message(chat_id, "📱 أرسل رقم هاتفك مع رمز الدولة (مثال: +1234567890):")
        
        elif telegram_manager.user_states.get(chat_id) == 'awaiting_phone':
            if text.startswith('+'):
                # إرسال الرمز
                result = run_async(telegram_manager.send_code_request(text, chat_id))
                if result[0]:
                    telegram_manager.user_states[chat_id] = 'awaiting_code'
                    send_telegram_message(chat_id, "🔐 تم إرسال الرمز إلى هاتفك. أرسل الرمز الآن:")
                else:
                    send_telegram_message(chat_id, result[1])
            else:
                send_telegram_message(chat_id, "❌ رقم غير صحيح. استخدم الصيغة: +1234567890")
        
        elif telegram_manager.user_states.get(chat_id) == 'awaiting_code':
            # تسجيل الدخول بالرمز
            result = run_async(telegram_manager.sign_in(chat_id, text))
            send_telegram_message(chat_id, result[1])
            if result[0]:
                telegram_manager.user_states[chat_id] = 'authenticated'
                send_telegram_message(chat_id, "🎉 يمكنك الآن استخدام /start_email لإرسال الرسائل")
        
        elif text.startswith('/start_email'):
            if telegram_manager.user_states.get(chat_id) == 'authenticated':
                email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
                if email_match:
                    email = email_match.group()
                    if bot_runner.start(email, chat_id):
                        send_telegram_message(chat_id, f"🚀 بدأ الإرسال باستخدام: {email}\n⚡ يعمل 24/7")
                    else:
                        send_telegram_message(chat_id, "⚠️ البوت يعمل بالفعل")
                else:
                    send_telegram_message(chat_id, "❌ صيغة البريد غير صحيحة. استخدم:\n/start_email example@gmail.com")
            else:
                send_telegram_message(chat_id, "❌ يجب تسجيل الدخول أولاً. أرسل /start")
        
        elif text == '/stop':
            if bot_runner.running:
                bot_runner.stop()
                send_telegram_message(chat_id, f"🛑 تم الإيقاف - عدد الرسائل: {bot_runner.message_count}")
            else:
                send_telegram_message(chat_id, "⚠️ البوت غير نشط")
        
        elif text == '/status':
            status = "✅ مصادق" if telegram_manager.user_states.get(chat_id) == 'authenticated' else "❌ غير مصادق"
            bot_status = "🟢 نشط" if bot_runner.running else "🔴 متوقف"
            message = f"""
📊 حالة الحساب:
المصادقة: {status}
البوت: {bot_status}
الرسائل المرسلة: {bot_runner.message_count}
            """.strip()
            send_telegram_message(chat_id, message)
        
        elif text == '/help':
            help_text = """
📋 أوامر البوت:
/start - بدء المصادقة
/start_email email - بدء الإرسال
/stop - إيقاف البوت
/status - عرض الحالة
/help - المساعدة
            """.strip()
            send_telegram_message(chat_id, help_text)
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)

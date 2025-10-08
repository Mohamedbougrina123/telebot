from flask import Flask, request, jsonify
import requests
import re
import os
import logging
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN', "8328267645:AAEgq7skSPifXizqPriMkiUt4oDPPm-I5R8")
API_ID = int(os.environ.get('API_ID', 22154260))
API_HASH = os.environ.get('API_HASH', '6bae7de9fdd9031aede658ec8a8b57c0')
SESSION_STRING = os.environ.get('SESSION_STRING', "1BJWap1wBu0nxM0elvffBxi7xF33DtYIJNQq8v4KAB41XaZUFMJGZg-jCSoUIqs7h9hVVZ87qfyzyN_GiM94CrKsD39jAbfmvyFu6Z7ACQyFc4mI8HzLa_aKqzj3Hp_w3jALn-jO8U2Iw3M16Jf9eGxlodcuDI2X0JyCSZZnZo2A2M7n3Hzs8UqQztsVywROKC1yIONoYJegwpjw1fUZ8H8iea4Pg-wyV6a8nWpgexnoZShXMrrfOZyT8n7qy6ajiaELEEikLO_v2DZ6uKA6JlHd-MUmW9AKaaeh4F6K6FW5GGorI3FEioA-DIwKGSx8jXBQPF7zBn11aZGfIbvR9z1hCKoB00Ns=")  # جلسة جاهزة
PORT = int(os.environ.get('PORT', 10000))

# تخزين البيانات
user_data = {}
telegram_client = None

def send_telegram_message(chat_id, text):
    """إرسال رسالة عبر بوت التلغرام"""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except:
        return False

async def init_telegram_client():
    """تهيئة عميل التلغرام"""
    global telegram_client
    try:
        if SESSION_STRING:
            # استخدام الجلسة الجاهزة
            session = StringSession(SESSION_STRING)
            telegram_client = TelegramClient(session, API_ID, API_HASH)
            await telegram_client.connect()
            
            if await telegram_client.is_user_authorized():
                logger.info("✅ تم الاتصال باستخدام الجلسة الجاهزة")
                return True
            else:
                logger.error("❌ الجلسة غير صالحة")
                return False
        else:
            # إنشاء عميل جديد (سيطلب تسجيل دخول)
            telegram_client = TelegramClient(StringSession(), API_ID, API_HASH)
            await telegram_client.connect()
            logger.info("🔑 يرجى تسجيل الدخول أولاً")
            return True
    except Exception as e:
        logger.error(f"❌ خطأ في تهيئة العميل: {e}")
        return False

async def send_telegram_message_async(text):
    """إرسال رسالة عبر Telethon"""
    global telegram_client
    try:
        if telegram_client and await telegram_client.is_user_authorized():
            await telegram_client.send_message('@fakemailbot', text)
            return True
        return False
    except Exception as e:
        logger.error(f"❌ خطأ في إرسال الرسالة: {e}")
        return False

def run_async(coro):
    """تشغيل دالة async"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# تهيئة العميل عند بدء التشغيل
def initialize_client():
    run_async(init_telegram_client())

# تشغيل التهيئة في thread منفصل
threading.Thread(target=initialize_client, daemon=True).start()

@app.route('/')
def home():
    return "🤖 البوت يعمل - Telethon جاهز!"

@app.route('/api/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        message = data.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '').strip()

        if not chat_id:
            return jsonify({"status": "error"})

        if chat_id not in user_data:
            user_data[chat_id] = {
                'running': False,
                'message_count': 0,
                'email': ''
            }

        user = user_data[chat_id]

        if text == '/start':
            if SESSION_STRING:
                send_telegram_message(chat_id, "🚀 البوت جاهز للعمل!\n\nأرسل:\n/start_email example@gmail.com")
            else:
                send_telegram_message(chat_id, "🔑 يرجى تسجيل الدخول أولاً\n\nأرسل /login لبدء المصادقة")

        elif text == '/login' and not SESSION_STRING:
            # كود المصادقة (إذا لم تكن هناك جلسة جاهزة)
            send_telegram_message(chat_id, "📱 أرسل رقم هاتفك مع رمز الدولة:\nمثال: +1234567890")
            user['state'] = 'awaiting_phone'

        elif text.startswith('/start_email'):
            email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
            if email_match:
                user['email'] = email_match.group()
                user['running'] = True
                
                # بدء الإرسال في thread منفصل
                def start_sending():
                    async def send_loop():
                        while user['running']:
                            try:
                                success = await send_telegram_message_async(user['email'])
                                if success:
                                    user['message_count'] += 1
                                    logger.info(f"📨 تم إرسال الرسالة #{user['message_count']}")
                                await asyncio.sleep(2)
                            except Exception as e:
                                await asyncio.sleep(5)
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(send_loop())
                
                threading.Thread(target=start_sending, daemon=True).start()
                
                send_telegram_message(chat_id, f"✅ بدأ الإرسال باستخدام:\n{user['email']}\n\n⚡ يعمل 24/7")

        elif text == '/stop':
            if user['running']:
                user['running'] = False
                send_telegram_message(chat_id, f"🛑 تم الإيقاف\nالرسائل: {user['message_count']}")

        elif text == '/status':
            status = "🟢 نشط" if user['running'] else "🔴 متوقف"
            session_status = "✅ جاهز" if telegram_client and run_async(telegram_client.is_user_authorized()) else "❌ غير جاهز"
            message = f"📊 الحالة:\nالبوت: {status}\nالجلسة: {session_status}\nالرسائل: {user['message_count']}"
            send_telegram_message(chat_id, message)

        elif text == '/help':
            help_text = """
📋 الأوامر:
/start_email email - بدء الإرسال
/stop - إيقاف البوت  
/status - عرض الحالة
/help - المساعدة
            """
            send_telegram_message(chat_id, help_text.strip())

        return jsonify({"status": "success"})

    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"status": "error"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)

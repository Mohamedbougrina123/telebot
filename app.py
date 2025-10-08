from flask import Flask, request, jsonify
import requests
import re
import os
import logging
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
import threading
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# المتغيرات الثابتة
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8328267645:AAEgq7skSPifXizqPriMkiUt4oDPPm-I5R8")
SESSION_STRING = "1BJWap1wBu0nxM0elvffBxi7xF33DtYIJNQq8v4KAB41XaZUFMJGZg-jCSoUIqs7h9hVVZ87qfyzyN_GiM94CrKsD39jAbfmvyFu6Z7ACQyFc4mI8HzLa_aKqzj3Hp_w3jALn-jO8U2Iw3M16Jf9eGxlodcuDI2X0JyCSZZnZo2A2M7n3Hzs8UqQztsVywROKC1yIONoYJegwpjw1fUZ8H8iea4Pg-wyV6a8nWpgexnoZShXMrrfOZyT8n7qy6ajiaELEEikLO_v2DZ6uKA6JlHd-MUmW9AKaaeh4F6K6FW5GGorI3FEioA-DIwKGSx8jXBQPF7zBn11aZGfIbvR9z1hCKoB00Ns="
API_ID = 22154260
API_HASH = '6bae7de9fdd9031aede658ec8a8b57c0'
PORT = int(os.environ.get('PORT', 10000))

# المتغيرات العامة
user_data = {}
telegram_client = None
client_ready = False
user_info = {}

def send_telegram_bot_message(chat_id, text):
    """إرسال رسالة عبر بوت التلغرام"""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Bot message error: {e}")
        return False

async def init_telegram():
    """تهيئة عميل التلغرام بالجلسة الجاهزة"""
    global telegram_client, client_ready, user_info
    
    try:
        logger.info("🚀 جاري تهيئة عميل التلغرام...")
        
        # استخدام الجلسة الجاهزة
        session = StringSession(SESSION_STRING)
        telegram_client = TelegramClient(session, API_ID, API_HASH)
        
        await telegram_client.connect()
        logger.info("✅ تم الاتصال بالسيرفر")
        
        # التحقق من صحة الجلسة
        if await telegram_client.is_user_authorized():
            me = await telegram_client.get_me()
            user_info = {
                'first_name': me.first_name,
                'last_name': me.last_name,
                'phone': me.phone,
                'id': me.id,
                'username': me.username
            }
            logger.info(f"✅ الجلسة صالحة - المستخدم: {me.first_name}")
            client_ready = True
            return True
        else:
            logger.error("❌ الجلسة غير صالحة")
            return False
            
    except Exception as e:
        logger.error(f"❌ خطأ في تهيئة العميل: {e}")
        return False

async def send_telegram_message(text):
    """إرسال رسالة عبر Telethon"""
    global telegram_client, client_ready
    
    if not client_ready or not telegram_client:
        logger.error("❌ العميل غير جاهز")
        return False
    
    try:
        await telegram_client.send_message('@fakemailbot', text)
        logger.info(f"✅ تم إرسال: {text}")
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في الإرسال: {e}")
        return False

async def test_session_command():
    """اختبار الجلسة - نفس كود الاختبار"""
    global telegram_client, user_info
    
    try:
        if not telegram_client:
            return "❌ العميل غير مهيأ"
        
        # التحقق من صحة الجلسة
        if await telegram_client.is_user_authorized():
            me = await telegram_client.get_me()
            user_info = {
                'first_name': me.first_name,
                'last_name': me.last_name,
                'phone': me.phone,
                'id': me.id,
                'username': me.username
            }
            
            result = [
                "✅ الجلسة صالحة",
                f"👤 المستخدم: {me.first_name} {me.last_name or ''}",
                f"📞 الرقم: {me.phone}",
                f"🆔 ID: {me.id}",
                f"🔗 username: @{me.username}" if me.username else "🔗 username: لا يوجد"
            ]
            
            # اختبار إرسال رسالة
            try:
                await telegram_client.send_message('@fakemailbot', 'test from session')
                result.append("✅ تم إرسال رسالة اختبار بنجاح")
            except Exception as e:
                result.append(f"❌ فشل إرسال الرسالة: {e}")
            
            return "\n".join(result)
        else:
            return "❌ الجلسة غير صالحة"
            
    except Exception as e:
        return f"💥 خطأ في الاختبار: {e}"

def run_async(coro):
    """تشغيل دالة async"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    except Exception as e:
        logger.error(f"Async error: {e}")
        return None
    finally:
        loop.close()

# بدء تهيئة العميل عند التشغيل
def start_client():
    logger.info("🔧 جاري تهيئة العميل...")
    success = run_async(init_telegram())
    if success:
        logger.info("🎉 تم تهيئة العميل بنجاح!")
    else:
        logger.error("💥 فشل في تهيئة العميل")

# تشغيل التهيئة في thread منفصل
threading.Thread(target=start_client, daemon=True).start()

@app.route('/')
def home():
    status = "✅ جاهز" if client_ready else "❌ غير جاهز"
    user_text = ""
    if user_info:
        user_text = f" - 👤 {user_info.get('first_name', '')}"
    return f"🤖 البوت يعمل - حالة الجلسة: {status}{user_text}"

@app.route('/test-session')
def test_session_route():
    """route لاختبار الجلسة"""
    if not client_ready:
        return jsonify({"status": "error", "message": "العميل غير جاهز"})
    
    result = run_async(test_session_command())
    return jsonify({"status": "success", "result": result})

@app.route('/api/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error"})

        message = data.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '').strip()

        if not chat_id:
            return jsonify({"status": "error"})

        # تهيئة بيانات المستخدم
        if chat_id not in user_data:
            user_data[chat_id] = {
                'running': False,
                'message_count': 0,
                'email': ''
            }

        user = user_data[chat_id]

        if text == '/start':
            if client_ready:
                user_info_text = ""
                if user_info:
                    user_info_text = f"\n👤 الجلسة: {user_info.get('first_name', '')} - {user_info.get('phone', '')}"
                
                send_telegram_bot_message(chat_id, 
                    f"🚀 البوت جاهز للعمل!{user_info_text}\n\n"
                    "📧 أرسل:\n"
                    "/start_email example@gmail.com\n\n"
                    "🔧 أوامر التحكم:\n"
                    "/test_session - اختبار الجلسة\n"
                    "/status - حالة البوت\n"
                    "/help - المساعدة")
            else:
                send_telegram_bot_message(chat_id, "⏳ البوت قيد التهيئة...")

        elif text == '/test_session':
            if client_ready:
                send_telegram_bot_message(chat_id, "🔄 جاري اختبار الجلسة...")
                result = run_async(test_session_command())
                send_telegram_bot_message(chat_id, result)
            else:
                send_telegram_bot_message(chat_id, "❌ العميل غير جاهز")

        elif text.startswith('/start_email'):
            if not client_ready:
                send_telegram_bot_message(chat_id, "⏳ البوت غير جاهز بعد")
                return jsonify({"status": "success"})

            email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
            if email_match:
                user['email'] = email_match.group()
                user['running'] = True
                
                # بدء الإرسال التلقائي
                def start_sending():
                    async def send_loop():
                        while user['running']:
                            try:
                                success = await send_telegram_message(user['email'])
                                if success:
                                    user['message_count'] += 1
                                    if user['message_count'] % 10 == 0:  # إعلام كل 10 رسائل
                                        logger.info(f"📨 تم إرسال {user['message_count']} رسالة")
                                await asyncio.sleep(3)
                            except Exception as e:
                                logger.error(f"Send error: {e}")
                                await asyncio.sleep(5)
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(send_loop())
                
                threading.Thread(target=start_sending, daemon=True).start()
                
                send_telegram_bot_message(chat_id, 
                    f"✅ بدأ الإرسال باستخدام:\n{user['email']}\n\n"
                    f"⚡ يعمل 24/7 تلقائياً\n\n"
                    f"لإيقاف البوت أرسل /stop")

        elif text == '/stop':
            if user['running']:
                user['running'] = False
                send_telegram_bot_message(chat_id, 
                    f"🛑 تم إيقاف البوت\n"
                    f"📊 عدد الرسائل المرسلة: {user['message_count']}")

        elif text == '/status':
            bot_status = "🟢 نشط" if user['running'] else "🔴 متوقف"
            session_status = "✅ جاهز" if client_ready else "❌ غير جاهز"
            
            status_msg = [
                f"📊 حالة البوت:",
                f"• البوت: {bot_status}",
                f"• الجلسة: {session_status}",
                f"• الرسائل: {user['message_count']}",
                f"• البريد: {user.get('email', 'لم يحدد')}"
            ]
            
            if user_info:
                status_msg.extend([
                    f"",
                    f"👤 معلومات الجلسة:",
                    f"• الاسم: {user_info.get('first_name', '')} {user_info.get('last_name', '')}",
                    f"• الرقم: {user_info.get('phone', '')}",
                    f"• ID: {user_info.get('id', '')}"
                ])
            
            send_telegram_bot_message(chat_id, "\n".join(status_msg))

        elif text == '/help':
            help_msg = [
                "📋 أوامر البوت:",
                "",
                "/start_email email - بدء الإرسال التلقائي",
                "/stop - إيقاف البوت",
                "/test_session - اختبار الجلسة",
                "/status - عرض الحالة الكاملة",
                "/help - المساعدة",
                "",
                "📝 مثال:",
                "/start_email test@gmail.com"
            ]
            send_telegram_bot_message(chat_id, "\n".join(help_msg))

        return jsonify({"status": "success"})

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)

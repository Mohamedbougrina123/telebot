from flask import Flask, request, jsonify
import requests
import re
import os
import logging
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

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
sending_tasks = {}
loop = None

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
        
        await telegram_client.start()
        logger.info("✅ تم بدء العميل بنجاح")
        
        # التحقق من صحة الجلسة
        if await telegram_client.is_user_authorized():
            me = await telegram_client.get_me()
            user_info = {
                'first_name': me.first_name or "",
                'last_name': me.last_name or "",
                'phone': me.phone or "",
                'id': me.id,
                'username': me.username or ""
            }
            logger.info(f"✅ الجلسة صالحة - المستخدم: {user_info['first_name']}")
            client_ready = True
            
            # اختبار إرسال رسالة
            try:
                await telegram_client.send_message('@fakemailbot', '🎯 جلسة جاهزة للعمل - Bot Started!')
                logger.info("✅ تم اختبار الإرسال بنجاح إلى @fakemailbot")
            except Exception as e:
                logger.error(f"❌ فشل في اختبار الإرسال: {e}")
            
            return True
        else:
            logger.error("❌ الجلسة غير صالحة")
            return False
            
    except Exception as e:
        logger.error(f"❌ خطأ في تهيئة العميل: {e}")
        return False

async def send_telegram_message(text):
    """إرسال رسالة عبر Telethon إلى @fakemailbot"""
    global telegram_client
    
    if not telegram_client:
        logger.error("❌ العميل غير موجود للإرسال")
        return False
    
    try:
        # التأكد من الاتصال
        if not telegram_client.is_connected():
            await telegram_client.connect()
        
        # إرسال الرسالة إلى البوت المحدد
        await telegram_client.send_message('@fakemailbot', text)
        logger.info(f"✅ تم إرسال الرسالة إلى @fakemailbot: {text}")
        return True
        
    except Exception as e:
        logger.error(f"❌ خطأ في إرسال الرسالة إلى @fakemailbot: {e}")
        return False

async def sending_loop(chat_id, email):
    """حلقة الإرسال للمستخدم"""
    user = user_data[chat_id]
    
    logger.info(f"🔄 بدء الإرسال لـ {chat_id} باستخدام: {email}")
    
    while user.get('running', False):
        try:
            success = await send_telegram_message(email)
            if success:
                user['message_count'] += 1
                logger.info(f"📨 {chat_id}: تم إرسال الرسالة #{user['message_count']} - {email}")
                
                # إرسال تحديث كل 5 رسائل
                if user['message_count'] % 5 == 0:
                    send_telegram_bot_message(chat_id, 
                        f"📊 تقدم الإرسال:\n"
                        f"• عدد الرسائل: {user['message_count']}\n"
                        f"• البريد: {email}\n"
                        f"• الحالة: 🟢 مستمر")
            
            await asyncio.sleep(2)  # انتظار 2 ثانية بين الرسائل
            
        except Exception as e:
            logger.error(f"❌ خطأ في الإرسال لـ {chat_id}: {e}")
            await asyncio.sleep(3)

async def test_session_command():
    """اختبار الجلسة مع اختبار إرسال فعلي"""
    global telegram_client, user_info
    
    try:
        if not telegram_client:
            return "❌ العميل غير موجود"
        
        # التحقق من صحة الجلسة
        if await telegram_client.is_user_authorized():
            me = await telegram_client.get_me()
            user_info = {
                'first_name': me.first_name or "",
                'last_name': me.last_name or "",
                'phone': me.phone or "",
                'id': me.id,
                'username': me.username or ""
            }
            
            result = [
                "🎉 اختبار الجلسة:",
                f"✅ الجلسة صالحة",
                f"👤 المستخدم: {user_info['first_name']} {user_info['last_name']}",
                f"📞 الرقم: {user_info['phone']}",
                f"🆔 ID: {user_info['id']}",
                f"🔗 username: @{user_info['username']}" if user_info['username'] else "🔗 username: لا يوجد"
            ]
            
            # اختبار إرسال رسالة فعلية
            try:
                test_message = "🧪 رسالة اختبار من الجلسة - Test Message"
                await telegram_client.send_message('@fakemailbot', test_message)
                result.append("✅ تم إرسال رسالة اختبار بنجاح إلى @fakemailbot")
                logger.info("✅ اختبار الإرسال ناجح")
            except Exception as e:
                result.append(f"❌ فشل إرسال الرسالة: {str(e)}")
                logger.error(f"❌ اختبار الإرسال فاشل: {e}")
            
            return "\n".join(result)
        else:
            return "❌ الجلسة غير صالحة أو منتهية"
            
    except Exception as e:
        return f"💥 خطأ في الاختبار: {str(e)}"

def initialize_client():
    """تهيئة العميل عند بدء التشغيل"""
    global loop, client_ready
    
    try:
        # إنشاء event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        logger.info("🔧 جاري تهيئة العميل...")
        success = loop.run_until_complete(init_telegram())
        if success:
            logger.info("🎉 تم تهيئة العميل بنجاح!")
            client_ready = True
        else:
            logger.error("💥 فشل في تهيئة العميل")
    except Exception as e:
        logger.error(f"💥 خطأ في التهيئة: {e}")

# تهيئة العميل مباشرة
initialize_client()

@app.route('/')
def home():
    status = "✅ جاهز" if client_ready else "❌ غير جاهز"
    user_text = ""
    if user_info:
        user_text = f" - 👤 {user_info.get('first_name', '')}"
    
    # حساب إجمالي الرسائل
    total_messages = sum(user['message_count'] for user in user_data.values())
    
    return f"🤖 البوت يعمل - حالة الجلسة: {status}{user_text} - 📧 الرسائل: {total_messages}"

@app.route('/test-session')
def test_session_route():
    """route لاختبار الجلسة"""
    if not client_ready:
        return jsonify({"status": "error", "message": "❌ العميل غير جاهز"})
    
    try:
        result = loop.run_until_complete(test_session_command())
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        return jsonify({"status": "error", "message": f"❌ خطأ: {str(e)}"})

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
            if not client_ready:
                send_telegram_bot_message(chat_id, "❌ العميل غير جاهز")
                return jsonify({"status": "success"})
            
            send_telegram_bot_message(chat_id, "🔄 جاري اختبار الجلسة والإرسال...")
            try:
                result = loop.run_until_complete(test_session_command())
                send_telegram_bot_message(chat_id, result)
            except Exception as e:
                send_telegram_bot_message(chat_id, f"❌ خطأ في الاختبار: {str(e)}")

        elif text.startswith('/start_email'):
            if not client_ready:
                send_telegram_bot_message(chat_id, "❌ العميل غير جاهز")
                return jsonify({"status": "success"})

            email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
            if email_match:
                user['email'] = email_match.group()
                user['running'] = True
                user['message_count'] = 0  # إعادة التعيين
                
                # إلغاء المهمة السابقة إذا كانت موجودة
                if chat_id in sending_tasks:
                    sending_tasks[chat_id].cancel()
                
                # بدء الإرسال التلقائي
                task = loop.create_task(sending_loop(chat_id, user['email']))
                sending_tasks[chat_id] = task
                
                send_telegram_bot_message(chat_id, 
                    f"🎯 بدأ الإرسال الفعلي!\n\n"
                    f"📧 البريد: {user['email']}\n"
                    f"🔗 الهدف: @fakemailbot\n"
                    f"⚡ السرعة: رسالة كل 2 ثانية\n\n"
                    f"📊 سيتم إعلامك كل 5 رسائل\n"
                    f"🛑 لإيقاف البوت أرسل /stop")
                
                logger.info(f"🎯 بدأ الإرسال لـ {chat_id}: {user['email']} إلى @fakemailbot")
                
            else:
                send_telegram_bot_message(chat_id, "❌ لم يتم العثور على بريد إلكتروني صحيح")

        elif text == '/stop':
            if user['running']:
                user['running'] = False
                if chat_id in sending_tasks:
                    sending_tasks[chat_id].cancel()
                    del sending_tasks[chat_id]
                
                send_telegram_bot_message(chat_id, 
                    f"🛑 تم إيقاف البوت\n\n"
                    f"📊 إحصائيات الإرسال:\n"
                    f"• عدد الرسائل المرسلة: {user['message_count']}\n"
                    f"• البريد المستخدم: {user.get('email', 'لم يحدد')}\n"
                    f"• الحالة: 🔴 متوقف")
                
                logger.info(f"🛑 توقف الإرسال لـ {chat_id} - الرسائل: {user['message_count']}")

        elif text == '/status':
            bot_status = "🟢 نشط" if user['running'] else "🔴 متوقف"
            session_status = "✅ جاهز" if client_ready else "❌ غير جاهز"
            
            status_msg = [
                f"📊 حالة البوت:",
                f"• البوت: {bot_status}",
                f"• الجلسة: {session_status}",
                f"• الرسائل المرسلة: {user['message_count']}",
                f"• البريد: {user.get('email', 'لم يحدد')}",
                f"• الهدف: @fakemailbot"
            ]
            
            if user_info and client_ready:
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
                "/start_email email - بدء الإرسال التلقائي إلى @fakemailbot",
                "/stop - إيقاف البوت وعرض الإحصائيات",
                "/test_session - اختبار الجلسة والإرسال",
                "/status - عرض الحالة الكاملة",
                "/help - المساعدة",
                "",
                "📝 مثال:",
                "/start_email test@gmail.com",
                "",
                "⚡ المميزات:",
                "• إرسال تلقائي كل 2 ثانية",
                "• تحديث الإحصائيات كل 5 رسائل",
                "• مراقبة في الوقت الفعلي"
            ]
            send_telegram_bot_message(chat_id, "\n".join(help_msg))

        return jsonify({"status": "success"})

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)

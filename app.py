from flask import Flask, request, jsonify
import requests
import re
import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

app = Flask(__name__)

BOT_TOKEN = "8328267645:AAEgq7skSPifXizqPriMkiUt4oDPPm-I5R8"
SESSION_STRING = "1BJWap1wBu0nxM0elvffBxi7xF33DtYIJNQq8v4KAB41XaZUFMJGZg-jCSoUIqs7h9hVVZ87qfyzyN_GiM94CrKsD39jAbfmvyFu6Z7ACQyFc4mI8HzLa_aKqzj3Hp_w3jALn-jO8U2Iw3M16Jf9eGxlodcuDI2X0JyCSZZnZo2A2M7n3Hzs8UqQztsVywROKC1yIONoYJegwpjw1fUZ8H8iea4Pg-wyV6a8nWpgexnoZShXMrrfOZyT8n7qy6ajiaELEEikLO_v2DZ6uKA6JlHd-MUmW9AKaaeh4F6K6FW5GGorI3FEioA-DIwKGSx8jXBQPF7zBn11aZGfIbvR9z1hCKoB00Ns="
API_ID = 22154260
API_HASH = '6bae7de9fdd9031aede658ec8a8b57c0'
PORT = int(os.environ.get('PORT', 10000))

user_data = {}
telegram_client = None
client_ready = False
user_info = {}
sending_tasks = {}

def send_telegram_bot_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    try:
        requests.post(url, json=payload, timeout=5)
        return True
    except:
        return False

async def init_telegram():
    global telegram_client, client_ready, user_info
    try:
        session = StringSession(SESSION_STRING)
        telegram_client = TelegramClient(session, API_ID, API_HASH)
        await telegram_client.start()
        
        if await telegram_client.is_user_authorized():
            me = await telegram_client.get_me()
            user_info = {
                'first_name': me.first_name or "",
                'phone': me.phone or "",
                'id': me.id
            }
            client_ready = True
            return True
        return False
    except Exception as e:
        print(f"Init error: {e}")
        return False

async def send_telegram_message(text):
    try:
        await telegram_client.send_message('@fakemailbot', text)
        return True
    except:
        return False

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

run_async(init_telegram())

async def sending_loop(chat_id, email):
    user = user_data[chat_id]
    
    while user.get('running', False):
        try:
            success = await send_telegram_message(email)
            if success:
                user['message_count'] += 1
                
                if user['message_count'] % 50 == 0:
                    send_telegram_bot_message(chat_id, f"تم إرسال {user['message_count']} رسالة")
            
            await asyncio.sleep(2)
        except:
            await asyncio.sleep(2)

def start_sending(chat_id, email):
    if chat_id in sending_tasks:
        sending_tasks[chat_id].cancel()
    
    task = asyncio.create_task(sending_loop(chat_id, email))
    sending_tasks[chat_id] = task

@app.route('/')
def home():
    return "Bot is running!"

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
            send_telegram_bot_message(chat_id, 
                "مرحبا! استخدم الأوامر التالية:\n\n"
                "/start_email email - بدء الإرسال\n"
                "/stop - إيقاف البوت\n"
                "/test_session - اختبار الجلسة\n"
                "/status - عرض الحالة\n"
                "/help - المساعدة\n\n"
                "مثال: /start_email test@gmail.com")

        elif text.startswith('/start_email'):
            if not client_ready:
                send_telegram_bot_message(chat_id, "الجلسة غير جاهزة")
                return jsonify({"status": "success"})

            email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
            if email_match:
                email = email_match.group()
                user['email'] = email
                user['running'] = True
                user['message_count'] = 0
                
                send_telegram_bot_message(chat_id, 
                    f"بدأ الإرسال إلى @fakemailbot\n"
                    f"البريد: {email}\n"
                    f"السرعة: كل 2 ثانية\n\n"
                    "سيستمر الإرسال حتى تستخدم /stop")
                
                run_async(sending_loop(chat_id, email))
                
            else:
                send_telegram_bot_message(chat_id, "لم يتم العثور على بريد إلكتروني. استخدم: /start_email test@gmail.com")

        elif text == '/stop':
            if user['running']:
                user['running'] = False
                if chat_id in sending_tasks:
                    sending_tasks[chat_id].cancel()
                
                send_telegram_bot_message(chat_id, 
                    f"تم إيقاف البوت\n"
                    f"الرسائل المرسلة: {user['message_count']}")

        elif text == '/test_session':
            if client_ready:
                result = run_async(send_telegram_message("رسالة اختبار من البوت"))
                if result:
                    send_telegram_bot_message(chat_id, 
                        "✅ اختبار الجلسة ناجح\n"
                        f"👤 المستخدم: {user_info.get('first_name', '')}\n"
                        f"📞 الرقم: {user_info.get('phone', '')}")
                else:
                    send_telegram_bot_message(chat_id, "❌ فشل في إرسال رسالة الاختبار")
            else:
                send_telegram_bot_message(chat_id, "❌ الجلسة غير جاهزة")

        elif text == '/status':
            bot_status = "🟢 نشط" if user['running'] else "🔴 متوقف"
            session_status = "✅ جاهزة" if client_ready else "❌ غير جاهزة"
            
            status_msg = [
                f"📊 حالة البوت:",
                f"• البوت: {bot_status}",
                f"• الجلسة: {session_status}",
                f"• الرسائل: {user['message_count']}",
                f"• البريد: {user.get('email', 'لا يوجد')}"
            ]
            
            send_telegram_bot_message(chat_id, "\n".join(status_msg))

        elif text == '/help':
            help_msg = [
                "📋 الأوامر المتاحة:",
                "",
                "/start_email email - بدء الإرسال إلى @fakemailbot",
                "/stop - إيقاف البوت وعرض الإحصائيات",
                "/test_session - اختبار الجلسة",
                "/status - عرض الحالة الكاملة",
                "/help - عرض هذه المساعدة",
                "",
                "📝 مثال:",
                "/start_email test@gmail.com",
                "",
                "⚡ المميزات:",
                "• إرسال تلقائي كل 2 ثانية",
                "• يستمر حتى يتم إيقافه",
                "• تحديثات كل 50 رسالة"
            ]
            send_telegram_bot_message(chat_id, "\n".join(help_msg))

        return jsonify({"status": "success"})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)

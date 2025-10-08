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

BOT_TOKEN = os.environ.get('BOT_TOKEN', "8328267645:AAEgq7skSPifXizqPriMkiUt4oDPPm-I5R8")
SESSION_STRING = "1BJWap1wBu0nxM0elvffBxi7xF33DtYIJNQq8v4KAB41XaZUFMJGZg-jCSoUIqs7h9hVVZ87qfyzyN_GiM94CrKsD39jAbfmvyFu6Z7ACQyFc4mI8HzLa_aKqzj3Hp_w3jALn-jO8U2Iw3M16Jf9eGxlodcuDI2X0JyCSZZnZo2A2M7n3Hzs8UqQztsVywROKC1yIONoYJegwpjw1fUZ8H8iea4Pg-wyV6a8nWpgexnoZShXMrrfOZyT8n7qy6ajiaELEEikLO_v2DZ6uKA6JlHd-MUmW9AKaaeh4F6K6FW5GGorI3FEioA-DIwKGSx8jXBQPF7zBn11aZGfIbvR9z1hCKoB00Ns="
API_ID = 22154260
API_HASH = '6bae7de9fdd9031aede658ec8a8b57c0'
PORT = int(os.environ.get('PORT', 10000))

user_data = {}
telegram_client = None
client_ready = False
user_info = {}
sending_tasks = {}
loop = None

def send_telegram_bot_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
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
                'last_name': me.last_name or "",
                'phone': me.phone or "",
                'id': me.id
            }
            client_ready = True
            return True
        else:
            return False
            
    except Exception as e:
        return False

async def send_telegram_message(text):
    global telegram_client
    if not telegram_client:
        return False
    try:
        await telegram_client.send_message('@fakemailbot', text)
        return True
    except Exception as e:
        return False

async def sending_loop(chat_id, email, count):
    user = user_data[chat_id]
    
    send_telegram_bot_message(chat_id, f"بدأ الإرسال: {email}\nالعدد: {count} رسالة")
    
    sent = 0
    while sent < count and user.get('running', False):
        try:
            success = await send_telegram_message(email)
            if success:
                sent += 1
                user['message_count'] = sent
                
                if sent % 100 == 0:
                    send_telegram_bot_message(chat_id, f"تم إرسال {sent} من {count} رسالة")
                
            await asyncio.sleep(2)
        except Exception as e:
            await asyncio.sleep(2)
    
    if sent >= count:
        send_telegram_bot_message(chat_id, f"تم الانتهاء من إرسال {count} رسالة بنجاح!")
        user['running'] = False

async def test_session_command():
    global telegram_client, user_info
    try:
        if not telegram_client:
            return "Client not available"
        
        if await telegram_client.is_user_authorized():
            me = await telegram_client.get_me()
            user_info = {
                'first_name': me.first_name or "",
                'phone': me.phone or ""
            }
            
            result = [
                "Session Test:",
                f"✅ Session valid",
                f"User: {user_info['first_name']}",
                f"Phone: {user_info['phone']}"
            ]
            
            try:
                await telegram_client.send_message('@fakemailbot', 'Test message from session')
                result.append("✅ Test message sent successfully")
            except Exception as e:
                result.append(f"❌ Message failed")
            
            return "\n".join(result)
        else:
            return "❌ Invalid session"
            
    except Exception as e:
        return f"Error"

def initialize_client():
    global loop, client_ready
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(init_telegram())
        if success:
            client_ready = True
    except Exception as e:
        pass

initialize_client()

@app.route('/')
def home():
    status = "✅ Ready" if client_ready else "❌ Not ready"
    total_messages = sum(user['message_count'] for user in user_data.values())
    return f"Bot Running - Status: {status} - Messages: {total_messages}"

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

        if chat_id not in user_data:
            user_data[chat_id] = {
                'running': False,
                'message_count': 0,
                'email': ''
            }

        user = user_data[chat_id]

        if text == '/start':
            send_telegram_bot_message(chat_id, 
                "أرسل:\n"
                "/run email@example.com 100\n"
                "حيث 100 هو عدد المرات المراد الإرسال")

        elif text.startswith('/run'):
            if not client_ready:
                send_telegram_bot_message(chat_id, "Client not ready")
                return jsonify({"status": "success"})

            parts = text.split()
            if len(parts) >= 3:
                email = parts[1]
                try:
                    count = int(parts[2])
                    if count > 0:
                        user['email'] = email
                        user['running'] = True
                        
                        if chat_id in sending_tasks:
                            sending_tasks[chat_id].cancel()
                        
                        task = loop.create_task(sending_loop(chat_id, email, count))
                        sending_tasks[chat_id] = task
                        
                    else:
                        send_telegram_bot_message(chat_id, "العدد يجب أن يكون أكبر من صفر")
                except ValueError:
                    send_telegram_bot_message(chat_id, "العدد غير صحيح")
            else:
                send_telegram_bot_message(chat_id, "استخدم: /run email@example.com 100")

        elif text == '/stop':
            if user['running']:
                user['running'] = False
                if chat_id in sending_tasks:
                    sending_tasks[chat_id].cancel()
                    del sending_tasks[chat_id]
                
                send_telegram_bot_message(chat_id, 
                    f"تم الإيقاف\n"
                    f"الرسائل المرسلة: {user['message_count']}")

        elif text == '/status':
            bot_status = "🟢 Active" if user['running'] else "🔴 Stopped"
            session_status = "✅ Ready" if client_ready else "❌ Not ready"
            
            status_msg = [
                f"الحالة:",
                f"البوت: {bot_status}",
                f"الجلسة: {session_status}",
                f"الرسائل: {user['message_count']}",
                f"البريد: {user.get('email', 'N/A')}"
            ]
            
            send_telegram_bot_message(chat_id, "\n".join(status_msg))

        return jsonify({"status": "success"})

    except Exception as e:
        return jsonify({"status": "error"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)

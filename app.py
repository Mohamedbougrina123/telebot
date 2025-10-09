from flask import Flask, request, jsonify
import requests
import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

app = Flask(__name__)
#lbayanat we kda ...
BOT_TOKEN = "7952626717:AAFphJU4Gb6bg4hdhwy9oActgwcmzCVrNaQ"
SESSION_STRING = "1BJWap1wBu5nDSgmxaqsqPYpwN9uKtixwdXnuX8YIaudahhSrUdFiYMSn2tF17VBGpYaB9taY2RnPc12lKRIBk_p93QL8LzdoudFE0_fSbZk0eo7B4EN2NLR18u__CYnDgEKrwoIQ8GAZXFJpnYE71lxqJR5u_o_kwyyUfDNHVk2tbUbGC0pETaxZAzQ_fmTQJwmMV2yPwuamCDCH7zMhVsBgLXu7QzDjcESIj13P_ocaCMZoadcBK07spzXEV-0gB85e-mLSwRTRVMETgMvmhri23Xmf5Qi1jXBAMdiZ9Z5irF0I__1WBTmF5mpSlau0uJF6O1AVi9pobvfNanbcKnLwLQdzip0="
API_ID = 29520252
API_HASH = '55a15121bb420b21c3f9e8ccabf964cf'
PORT = int(os.environ.get('PORT', 10000))

user_data = {}
client_ready = False
user_info = {}

def send_telegram_bot_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    try:
        requests.post(url, json=payload, timeout=5)
        return True
    except:
        return False

async def send_telegram_message(text):
    try:
        session = StringSession(SESSION_STRING)
        client = TelegramClient(session, API_ID, API_HASH)
        await client.start()
        await client.send_message('@fakemailbot', text)
        await client.disconnect()
        return True
    except Exception as e:
        print(f"Send error: {e}")
        return False

async def sending_loop(email, chat_id):
    user = user_data[chat_id]
    
    while user.get('running', False):
        try:
            success = await send_telegram_message(email)
            if success:
                user['message_count'] += 1
                
                if user['message_count'] % 20 == 0:
                    send_telegram_bot_message(chat_id, f"تم إرسال {user['message_count']} رسالة")
            
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Loop error: {e}")
            await asyncio.sleep(1)

def start_sending_loop(email, chat_id):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(sending_loop(email, chat_id))

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
            parts = text.split()
            if len(parts) >= 2:
                email = parts[1]
                user['email'] = email
                user['running'] = True
                user['message_count'] = 0
                
                send_telegram_bot_message(chat_id, 
                    f"بدأ الإرسال إلى @fakemailbot\n"
                    f"البريد: {email}\n"
                    f"السرعة: كل 1 ثانية\n\n"
                    "سيستمر الإرسال حتى تستخدم /stop\nBy Mohamed Bougrina !")
                
                import threading
                thread = threading.Thread(target=start_sending_loop, args=(email, chat_id))
                thread.daemon = True
                thread.start()
                
            else:
                send_telegram_bot_message(chat_id, "استخدم: /start_email test@gmail.com")

        elif text == '/stop':
            if user['running']:
                user['running'] = False
                send_telegram_bot_message(chat_id, 
                    f"تم إيقاف البوت\n"
                    f"الرسائل المرسلة: {user['message_count']}")

        elif text == '/test_session':
            send_telegram_bot_message(chat_id, "جاري اختبار الجلسة...")
            success = asyncio.run(send_telegram_message("رسالة اختبار من البوت"))
            if success:
                send_telegram_bot_message(chat_id, "✅ اختبار الجلسة ناجح - تم إرسال رسالة اختبار")
            else:
                send_telegram_bot_message(chat_id, "❌ فشل في اختبار الجلسة")

        elif text == '/status':
            bot_status = "🟢 نشط" if user['running'] else "🔴 متوقف"
            
            status_msg = [
                f"📊 حالة البوت:",
                f"• البوت: {bot_status}",
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
                "/status - عرض الحالة",
                "/help - المساعدة",
                "",
                "📝 مثال:",
                "/start_email test@gmail.com"
            ]
            send_telegram_bot_message(chat_id, "\n".join(help_msg))

        return jsonify({"status": "success"})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)

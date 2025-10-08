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
        logger.error(f"Bot message error: {e}")
        return False

async def init_telegram():
    global telegram_client, client_ready, user_info
    try:
        logger.info("Starting Telegram client...")
        session = StringSession(SESSION_STRING)
        telegram_client = TelegramClient(session, API_ID, API_HASH)
        await telegram_client.start()
        logger.info("Client started successfully")
        
        if await telegram_client.is_user_authorized():
            me = await telegram_client.get_me()
            user_info = {
                'first_name': me.first_name or "",
                'last_name': me.last_name or "",
                'phone': me.phone or "",
                'id': me.id,
                'username': me.username or ""
            }
            logger.info(f"Session valid - User: {user_info['first_name']}")
            client_ready = True
            
            try:
                await telegram_client.send_message('@fakemailbot', 'Bot Started - Session Ready')
                logger.info("Test message sent successfully")
            except Exception as e:
                logger.error(f"Test message failed: {e}")
            
            return True
        else:
            logger.error("Invalid session")
            return False
            
    except Exception as e:
        logger.error(f"Client init error: {e}")
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

async def sending_loop(chat_id, email):
    user = user_data[chat_id]
    logger.info(f"Starting sending loop for {chat_id}: {email}")
    
    while user.get('running', False):
        try:
            success = await send_telegram_message(email)
            if success:
                user['message_count'] += 1
                if user['message_count'] % 10 == 0:
                    send_telegram_bot_message(chat_id, f"Progress: {user['message_count']} messages sent")
            await asyncio.sleep(2)
        except Exception as e:
            await asyncio.sleep(2)

async def test_session_command():
    global telegram_client, user_info
    try:
        if not telegram_client:
            return "Client not available"
        
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
                "Session Test:",
                f"✅ Session valid",
                f"User: {user_info['first_name']} {user_info['last_name']}",
                f"Phone: {user_info['phone']}",
                f"ID: {user_info['id']}"
            ]
            
            try:
                await telegram_client.send_message('@fakemailbot', 'Test message from session')
                result.append("✅ Test message sent successfully")
            except Exception as e:
                result.append(f"❌ Message failed: {str(e)}")
            
            return "\n".join(result)
        else:
            return "❌ Invalid session"
            
    except Exception as e:
        return f"Error: {str(e)}"

def initialize_client():
    global loop, client_ready
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.info("Initializing client...")
        success = loop.run_until_complete(init_telegram())
        if success:
            logger.info("Client ready!")
            client_ready = True
        else:
            logger.error("Client init failed")
    except Exception as e:
        logger.error(f"Init error: {e}")

initialize_client()

@app.route('/')
def home():
    status = "✅ Ready" if client_ready else "❌ Not ready"
    user_text = ""
    if user_info:
        user_text = f" - {user_info.get('first_name', '')}"
    total_messages = sum(user['message_count'] for user in user_data.values())
    return f"Bot Running - Status: {status}{user_text} - Messages: {total_messages}"

@app.route('/test-session')
def test_session_route():
    if not client_ready:
        return jsonify({"status": "error", "message": "Client not ready"})
    try:
        result = loop.run_until_complete(test_session_command())
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error: {str(e)}"})

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
            if client_ready:
                user_info_text = ""
                if user_info:
                    user_info_text = f"\nSession: {user_info.get('first_name', '')}"
                
                send_telegram_bot_message(chat_id, 
                    f"Bot Ready!{user_info_text}\n\n"
                    "Send:\n"
                    "/start_email example@gmail.com")
            else:
                send_telegram_bot_message(chat_id, "Bot initializing...")

        elif text == '/test_session':
            if not client_ready:
                send_telegram_bot_message(chat_id, "Client not ready")
                return jsonify({"status": "success"})
            
            send_telegram_bot_message(chat_id, "Testing session...")
            try:
                result = loop.run_until_complete(test_session_command())
                send_telegram_bot_message(chat_id, result)
            except Exception as e:
                send_telegram_bot_message(chat_id, f"Test error: {str(e)}")

        elif text.startswith('/start_email'):
            if not client_ready:
                send_telegram_bot_message(chat_id, "Client not ready")
                return jsonify({"status": "success"})

            email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
            if email_match:
                user['email'] = email_match.group()
                user['running'] = True
                user['message_count'] = 0
                
                if chat_id in sending_tasks:
                    sending_tasks[chat_id].cancel()
                
                task = loop.create_task(sending_loop(chat_id, user['email']))
                sending_tasks[chat_id] = task
                
                send_telegram_bot_message(chat_id, 
                    f"Started sending!\n\n"
                    f"Email: {user['email']}\n"
                    f"Target: @fakemailbot\n"
                    f"Speed: Every 2 seconds\n\n"
                    f"Send /stop to stop")
                
                logger.info(f"Started sending for {chat_id}: {user['email']}")
                
            else:
                send_telegram_bot_message(chat_id, "Invalid email format")

        elif text == '/stop':
            if user['running']:
                user['running'] = False
                if chat_id in sending_tasks:
                    sending_tasks[chat_id].cancel()
                    del sending_tasks[chat_id]
                
                send_telegram_bot_message(chat_id, 
                    f"Stopped!\n"
                    f"Messages sent: {user['message_count']}\n"
                    f"Email: {user.get('email', 'N/A')}")
                
                logger.info(f"Stopped sending for {chat_id} - Messages: {user['message_count']}")

        elif text == '/status':
            bot_status = "🟢 Active" if user['running'] else "🔴 Stopped"
            session_status = "✅ Ready" if client_ready else "❌ Not ready"
            
            status_msg = [
                f"Bot Status:",
                f"Bot: {bot_status}",
                f"Session: {session_status}",
                f"Messages: {user['message_count']}",
                f"Email: {user.get('email', 'N/A')}",
                f"Target: @fakemailbot"
            ]
            
            if user_info and client_ready:
                status_msg.extend([
                    f"",
                    f"Session Info:",
                    f"Name: {user_info.get('first_name', '')} {user_info.get('last_name', '')}",
                    f"Phone: {user_info.get('phone', '')}",
                    f"ID: {user_info.get('id', '')}"
                ])
            
            send_telegram_bot_message(chat_id, "\n".join(status_msg))

        elif text == '/help':
            help_msg = [
                "Commands:",
                "/start_email email - Start sending to @fakemailbot",
                "/stop - Stop bot and show stats",
                "/test_session - Test session",
                "/status - Show status",
                "/help - Help",
                "",
                "Example:",
                "/start_email test@gmail.com"
            ]
            send_telegram_bot_message(chat_id, "\n".join(help_msg))

        return jsonify({"status": "success"})

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)

from flask import Flask, request, jsonify
import requests
import asyncio
from telethon import TelegramClient
import threading
import time
import re

app = Flask(__name__)

BOT_TOKEN = "8328267645:AAEgq7skSPifXizqPriMkiUt4oDPPm-I5R8"
WEBHOOK_URL = "https://telebot-cbyyl3it6-mohamed-bougrina-s-projects.vercel.app/api/webhook"
API_ID = 29520252
API_HASH = '55a15121bb420b21c3f9e8ccabf964cf'
PHONE_NUMBER = '+212669720067'

class BotManager:
    def __init__(self):
        self.running = False
        self.loop_count = 0
        self.current_email = ""
    
    async def send_message(self, text):
        async with TelegramClient('session_x', API_ID, API_HASH) as client:
            await client.start(phone=PHONE_NUMBER)
            await client.send_message('@fakemailbot', text)
    
    def start_bot(self, email):
        self.running = True
        self.loop_count = 0
        self.current_email = email
        
        async def run_bot():
            while self.running:
                try:
                    await self.send_message(email)
                    self.loop_count += 1
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"Error: {e}")
                    await asyncio.sleep(5)
        
        def start_loop():
            asyncio.run(run_bot())
        
        thread = threading.Thread(target=start_loop)
        thread.daemon = True
        thread.start()
    
    def stop_bot(self):
        self.running = False

bot_manager = BotManager()

@app.route('/api/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Webhook is active! ✅"
    
    try:
        data = request.get_json()
        print(f"Received data: {data}")
        
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            text = message.get('text', '').strip()
            
            print(f"Message from {chat_id}: {text}")
            
            if text.startswith('/start'):
                handle_start(chat_id, text)
            elif text == '/stop':
                handle_stop(chat_id)
            elif text == '/status':
                handle_status(chat_id)
            elif text == '/help':
                handle_help(chat_id)
            else:
                send_message(chat_id, "❌ Unknown command")
    
    except Exception as e:
        print(f"Webhook error: {e}")
    
    return jsonify({"status": "success"}), 200

def handle_start(chat_id, text):
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    
    if not email_match:
        send_message(chat_id, "❌ Usage: /start email@gmail.com")
        return
    
    email = email_match.group()
    
    if bot_manager.running:
        send_message(chat_id, f"⚠️ Bot already running with: {bot_manager.current_email}")
        return
    
    bot_manager.start_bot(email)
    send_message(chat_id, f"✅ Started with: {email}")

def handle_stop(chat_id):
    if not bot_manager.running:
        send_message(chat_id, "❌ Bot not running")
        return
    
    bot_manager.stop_bot()
    send_message(chat_id, f"⏹️ Stopped - Total messages: {bot_manager.loop_count}")

def handle_status(chat_id):
    status = "🟢 Running" if bot_manager.running else "🔴 Stopped"
    email_info = f" with: {bot_manager.current_email}" if bot_manager.running else ""
    message = f"Status: {status}{email_info}\nMessage count: {bot_manager.loop_count}"
    send_message(chat_id, message)

def handle_help(chat_id):
    help_text = """
🤖 Bot Commands:

/start email - Start bot with email
/stop - Stop bot  
/status - Show bot status
/help - Show this help message

Example: /start test@gmail.com
"""
    send_message(chat_id, help_text)

def send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Message sent to {chat_id}: {response.status_code}")
    except Exception as e:
        print(f"Error sending message: {e}")

def set_webhook():
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook'
    payload = {'url': WEBHOOK_URL}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Webhook set: {response.status_code}")
        print(f"Webhook response: {response.json()}")
    except Exception as e:
        print(f"Webhook error: {e}")

# تشغيل Flask بشكل مختلف لـ Vercel
if __name__ == '__main__':
    set_webhook()
    app.run(host='0.0.0.0', port=5000, debug=True)

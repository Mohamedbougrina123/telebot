from flask import Flask, request, jsonify
import requests
import asyncio
from telethon import TelegramClient
import threading
import time
import re
import os

app = Flask(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
API_ID = 29520252
API_HASH = '55a15121bb420b21c3f9e8ccabf964cf'
PHONE_NUMBER = '+212669720067'

class BotManager:
    def __init__(self):
        self.running = False
        self.loop_count = 0
    
    async def send_message(self, text):
        async with TelegramClient('session_x', API_ID, API_HASH) as client:
            await client.start(phone=PHONE_NUMBER)
            await client.send_message('@fakemailbot', text)
    
    def start_bot(self, email):
        self.running = True
        self.loop_count = 0
        
        async def run_bot():
            while self.running:
                try:
                    await self.send_message(email)
                    self.loop_count += 1
                    await asyncio.sleep(1)
                except Exception as e:
                    await asyncio.sleep(5)
        
        def start_loop():
            asyncio.run(run_bot())
        
        thread = threading.Thread(target=start_loop)
        thread.daemon = True
        thread.start()
        return thread
    
    def stop_bot(self):
        self.running = False

bot_manager = BotManager()

@app.route('/')
def home():
    return "Bot Running"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    
    if 'message' in data:
        message = data['message']
        chat_id = message['chat']['id']
        text = message.get('text', '').strip()
        
        user_id = message['from']['id']
        if not is_authorized_user(user_id):
            send_message(chat_id, "❌ Unauthorized")
            return jsonify({"status": "success"}), 200
        
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
    
    return jsonify({"status": "success"}), 200

def handle_start(chat_id, text):
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    
    if not email_match:
        send_message(chat_id, "❌ Usage: /start email@gmail.com")
        return
    
    email = email_match.group()
    
    if bot_manager.running:
        send_message(chat_id, "⚠️ Bot already running")
        return
    
    bot_manager.start_bot(email)
    send_message(chat_id, f"✅ Started with: {email}")

def handle_stop(chat_id):
    if not bot_manager.running:
        send_message(chat_id, "❌ Bot not running")
        return
    
    bot_manager.stop_bot()
    send_message(chat_id, f"⏹️ Stopped - Count: {bot_manager.loop_count}")

def handle_status(chat_id):
    status = "🟢 Running" if bot_manager.running else "🔴 Stopped"
    message = f"Status: {status}\nCount: {bot_manager.loop_count}"
    send_message(chat_id, message)

def handle_help(chat_id):
    help_text = """
/start email - Start bot
/stop - Stop bot  
/status - Show status
/help - This help
"""
    send_message(chat_id, help_text)

def is_authorized_user(user_id):
    authorized_users = [123456789]
    return user_id in authorized_users

def send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    
    try:
        requests.post(url, json=payload)
    except:
        pass

def set_webhook():
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook'
    payload = {'url': WEBHOOK_URL}
    
    try:
        requests.post(url, json=payload)
    except:
        pass

def auto_restart():
    def checker():
        while True:
            time.sleep(60)
    
    thread = threading.Thread(target=checker)
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
    set_webhook()
    auto_restart()
    app.run(host='0.0.0.0', port=5000, debug=False)

from flask import Flask, request, jsonify
import requests
import re
import threading
import time
import asyncio
from telethon import TelegramClient

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
        self.client = None
    
    async def init_telethon(self):
        """تهيئة Telethon"""
        try:
            self.client = TelegramClient('session_name', API_ID, API_HASH)
            await self.client.start(phone=PHONE_NUMBER)
            print("✅ Telethon connected successfully")
            return True
        except Exception as e:
            print(f"❌ Telethon error: {e}")
            return False
    
    async def send_telethon_message(self, text):
        """إرسال رسالة عبر Telethon"""
        try:
            if self.client and self.client.is_connected():
                await self.client.send_message('@fakemailbot', text)
                return True
            else:
                print("❌ Telethon client not connected")
                return False
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return False
    
    def start_bot(self, email):
        self.running = True
        self.loop_count = 0
        self.current_email = email
        
        async def run_async():
            # تهيئة Telethon
            if not await self.init_telethon():
                return
            
            # حلقة الإرسال
            while self.running:
                try:
                    success = await self.send_telethon_message(email)
                    if success:
                        self.loop_count += 1
                        print(f"✅ Sent: {email} - Count: {self.loop_count}")
                    await asyncio.sleep(3)
                except Exception as e:
                    print(f"❌ Loop error: {e}")
                    await asyncio.sleep(1)
        
        def start_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run_async())
            except Exception as e:
                print(f"❌ Async loop error: {e}")
            finally:
                loop.close()
        
        thread = threading.Thread(target=start_loop)
        thread.daemon = True
        thread.start()
    
    def stop_bot(self):
        self.running = False
        if self.client:
            asyncio.run(self.client.disconnect())

bot_manager = BotManager()

@app.route('/')
def home():
    return "🤖 Telegram Bot is Running on Vercel!"

@app.route('/api/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "✅ Webhook is active and ready!"
    
    try:
        data = request.get_json()
        print(f"📩 Received data: {data}")
        
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            text = message.get('text', '').strip()
            
            print(f"💬 Message from {chat_id}: {text}")
            
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
        print(f"❌ Webhook error: {e}")
    
    return jsonify({"status": "success"})

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
    send_message(chat_id, f"✅ Started with: {email}\n🤖 Bot is now sending messages to @fakemailbot")

def handle_stop(chat_id):
    if not bot_manager.running:
        send_message(chat_id, "❌ Bot not running")
        return
    
    bot_manager.stop_bot()
    send_message(chat_id, f"⏹️ Stopped - Total messages sent: {bot_manager.loop_count}")

def handle_status(chat_id):
    status = "🟢 Running" if bot_manager.running else "🔴 Stopped"
    email_info = f" with: {bot_manager.current_email}" if bot_manager.running else ""
    message = f"Status: {status}{email_info}\n📊 Message count: {bot_manager.loop_count}"
    send_message(chat_id, message)

def handle_help(chat_id):
    help_text = """
🤖 Bot Commands:

/start email - Start bot with email
/stop - Stop bot  
/status - Show bot status
/help - Show this help message

Example: 
/start test@gmail.com

📝 The bot will send the email repeatedly to @fakemailbot
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
        print(f"📤 Message sent to {chat_id}: {response.status_code}")
    except Exception as e:
        print(f"❌ Error sending message: {e}")

def set_webhook():
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook'
    payload = {'url': WEBHOOK_URL}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"🌐 Webhook set: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Webhook result: {result}")
    except Exception as e:
        print(f"❌ Webhook error: {e}")

# تعيين الويب هوك عند التشغيل
set_webhook()

if __name__ == '__main__':
    app.run(debug=True)

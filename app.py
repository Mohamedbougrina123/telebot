from flask import Flask, request, jsonify
import requests
import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

app = Flask(__name__)

BOT_TOKEN = "8328267645:AAEgq7skSPifXizqPriMkiUt4oDPPm-I5R8"
SESSION_STRING = "1BJWap1wBu0nxM0elvffBxi7xF33DtYIJNQq8v4KAB41XaZUFMJGZg-jCSoUIqs7h9hVVZ87qfyzyN_GiM94CrKsD39jAbfmvyFu6Z7ACQyFc4mI8HzLa_aKqzj3Hp_w3jALn-jO8U2Iw3M16Jf9eGxlodcuDI2X0JyCSZZnZo2A2M7n3Hzs8UqQztsVywROKC1yIONoYJegwpjw1fUZ8H8iea4Pg-wyV6a8nWpgexnoZShXMrrfOZyT8n7qy6ajiaELEEikLO_v2DZ6uKA6JlHd-MUmW9AKaaeh4F6K6FW5GGorI3FEioA-DIwKGSx8jXBQPF7zBn11aZGfIbvR9z1hCKoB00Ns="
API_ID = 22154260
API_HASH = '6bae7de9fdd9031aede658ec8a8b57c0'

user_data = {}

def send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    try:
        requests.post(url, json=payload)
        return True
    except:
        return False

async def send_to_fakemail(text):
    try:
        session = StringSession(SESSION_STRING)
        client = TelegramClient(session, API_ID, API_HASH)
        await client.start()
        await client.send_message('@fakemailbot', text)
        await client.disconnect()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

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

        if text == '/start':
            send_message(chat_id, "مرحبا! أرسل /send test@gmail.com 10")

        elif text.startswith('/send'):
            parts = text.split()
            if len(parts) == 3:
                email = parts[1]
                count = int(parts[2])
                
                send_message(chat_id, f"بدأ الإرسال: {email} - {count} مرة")
                
                success_count = 0
                for i in range(count):
                    result = asyncio.run(send_to_fakemail(email))
                    if result:
                        success_count += 1
                    
                    if (i + 1) % 10 == 0:
                        send_message(chat_id, f"تم إرسال {i + 1} من {count}")
                
                send_message(chat_id, f"تم الانتهاء! أرسلت {success_count} رسالة بنجاح")
                
            else:
                send_message(chat_id, "استخدم: /send email@example.com 10")

        return jsonify({"status": "success"})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=False)

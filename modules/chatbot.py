# modules/chatbot.py
from flask import request, jsonify
from langchain_openai import ChatOpenAI
import openai
from dotenv import load_dotenv
from datetime import datetime
import json
import re
import shutil


# بارگذاری متغیرهای محیطی
load_dotenv()

# تنظیمات AvalAI API
AVALAI_API_KEY = "aa-OIK6fjtJytf8zV5lcsdge2OefR38jQF8INNtNbs120am3fm6"
AVALAI_API_BASE_URL = "https://api.avalai.ir/v1"

openai.api_key = AVALAI_API_KEY
openai.api_base = AVALAI_API_BASE_URL

# تنظیمات LangChain برای AvalAI
llm = ChatOpenAI(
    model_name="gpt-4o-mini-2024-07-18",  # نام مدل AvalAI
    openai_api_key=AVALAI_API_KEY,
    openai_api_base=AVALAI_API_BASE_URL
)

def get_today_date():
    today = datetime.today()
    return today.strftime("%Y-%m-%d")  # فرمت تاریخ: سال-ماه-روز



# تابع ذخیره خروجی به شکل JSON
def save_event_details_to_json(event_details):
    # مسیر فایل JSON اصلی و فایل پشتیبان
    file_path = "event_details.json"
    backup_file_path = "backup_event_details.json"
    
    # تلاش برای باز کردن فایل و خواندن داده‌ها
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            # در صورتی که فایل موجود باشد، داده‌ها را بارگیری می‌کنیم
            existing_data = json.load(file)
    except FileNotFoundError:
        # اگر فایل پیدا نشد، داده‌های جدید را به صورت یک لیست خالی شروع می‌کنیم
        existing_data = []

    # استخراج داده‌های JSON از متن ورودی
    match = re.search(r'(\{.*\})', event_details, re.DOTALL)
    
    if match:
        # اگر داده‌ها پیدا شوند، آن‌ها را به صورت JSON تجزیه می‌کنیم
        event_data = json.loads(match.group(1))

        # اضافه کردن اطلاعات جدید به داده‌های موجود
        existing_data.append(event_data)

        # انتقال محتوای فعلی به فایل پشتیبان
        with open(backup_file_path, "w", encoding="utf-8") as backup_file:
            json.dump(existing_data, backup_file, ensure_ascii=False, indent=4)

        # حذف داده‌های قدیمی از فایل اصلی
        open(file_path, "w").close()

        # ذخیره کردن داده‌های جدید فقط در فایل اصلی
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump([event_data], file, ensure_ascii=False, indent=4)  # فقط داده جدید در فایل اصلی ذخیره می‌شود
    else:
        print("هیچ داده JSON معتبر پیدا نشد.")



# تابع برای پردازش متن و استخراج اطلاعات رویداد
def extract_event_details(text):
    today_date = get_today_date()  # گرفتن تاریخ امروز
    response = llm.predict(f"""
    Today is: '{today_date}'. Based on today. Please extract the event details from the following text:
    1. Title of the event
    2. Start Date and Time (in ISO 8601 format: YYYY-MM-DDTHH:MM:SS)
    3. End Date and Time (in ISO 8601 format: YYYY-MM-DDTHH:MM:SS)
    4. Description of the event
    5. Location of the event
    
    Please format the output as a JSON object like this and nothing else:

    {{
        "summary": "Event Title",
        "start": {{
            "dateTime": "YYYY-MM-DDTHH:MM:SS",
            "timeZone": "Asia/Tehran"  # منطقه زمانی را اضافه کنید
        }},
        "end": {{
            "dateTime": "YYYY-MM-DDTHH:MM:SS",
            "timeZone": "Asia/Tehran"  # منطقه زمانی را اضافه کنید
        }},
        "location": "Event Location",
        "description": "Event Description"
    }}

    Text to analyze: '{text}'
    """)
    save_event_details_to_json(response)
    return response

# پردازش درخواست‌های کاربر در چت‌بات
def ask_chatbot(user_input):
    event_details = extract_event_details(user_input)
    return event_details

# modules/chatbot.py
from flask import request, jsonify
from langchain_openai import ChatOpenAI
import openai
from dotenv import load_dotenv
from datetime import datetime
import json
import re
import pytz
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
    # تنظیم منطقه زمانی ایران
    iran_tz = pytz.timezone('Asia/Tehran')

    # دریافت تاریخ و ساعت کنونی به وقت ایران
    iran_time = datetime.now(iran_tz)

    # فرمت تاریخ و زمان: سال-ماه-روز ساعت:دقیقه
    return iran_time.strftime("%Y-%m-%d %H:%M")  # فرمت تاریخ: سال-ماه-روز ساعت:دقیقه



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
    today_date = get_today_date()  # دریافت تاریخ امروز
    response = llm.predict(f"""
    Today is: '{today_date}'. Based on today, please extract the event details from the following text:
    
    1. **Title of the event**: A short, clear name for the event.
    2. **Start Date and Time**: Extract in ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
    3. **End Date and Time**: Extract in ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
    4. **Description**: A brief explanation of the event.
    5. **Location**: If a location is mentioned, extract it.
    6. **Recurrence Rule (`RRULE`)**: If the event repeats, extract the pattern:
       - If it repeats weekly on multiple days, use "BYDAY=XX,XX,XX" format.
       - **Ensure that "SA" is used for Saturday and "SU" is used for Sunday**.
       - If the event lasts for multiple weeks, set COUNT as (weeks × number of days per week).
       - If it is a daily repetition, use "FREQ=DAILY;COUNT=N".
       - If it is a monthly or yearly event, format it properly.
       - If no recurrence is found, return an empty list.
    7. **Event Color (`colorId`)**:
       Assign a color based on event type:
       - **Work-related events** → `"1"` (Light Blue)
       - **Health, medical, fitness** → `"2"` (Green)
       - **Personal projects, planning** → `"3"` (Purple)
       - **Urgent deadlines, critical events** → `"4"` (Red)
       - **Reminders, small tasks** → `"5"` (Yellow)
       - **Important appointments, client meetings** → `"6"` (Orange)
       - **Travel, vacations, leisure** → `"7"` (Turquoise)
       - **Routine tasks, general admin work** → `"8"` (Gray)
       - **Education, courses, training** → `"9"` (Dark Blue)
       - **Celebrations, special occasions** → `"10"` (Pink)
       - **Strategic meetings, long-term planning** → `"11"` (Indigo)
       - If no specific category is found, assign a reasonable default color.

    **📌 Format the output strictly as a JSON object like this and nothing else:**
    
    {{
        "summary": "Event Title",
        "start": {{
            "dateTime": "YYYY-MM-DDTHH:MM:SS",
            "timeZone": "Asia/Tehran"
        }},
        "end": {{
            "dateTime": "YYYY-MM-DDTHH:MM:SS",
            "timeZone": "Asia/Tehran"
        }},
        "location": "Event Location",
        "description": "Event Description",
        "recurrence": ["RRULE:FREQ=...;BYDAY=XX,XX;COUNT=N"] or [],
        "colorId": "X"
    }}

    Text to analyze: '{text}'
    """)


    save_event_details_to_json(response)
    return response

# پردازش درخواست‌های کاربر در چت‌بات
def ask_chatbot(user_input):
    event_details = extract_event_details(user_input)
    return event_details

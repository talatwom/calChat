# modules/chatbot.py
from flask import request, jsonify
from langchain_openai import ChatOpenAI
import openai
from dotenv import load_dotenv
from datetime import datetime
import json
import re
import pytz
import threading

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

# ایجاد قفل برای هماهنگ‌سازی دسترسی به فایل‌ها در صورت استفاده از چندین درخواست همزمان
file_lock = threading.Lock()

def get_today_date():
    """
    دریافت تاریخ امروز به فرمت ISO 8601 (با 'T' به عنوان جداکننده و شامل ثانیه)
    """
    iran_tz = pytz.timezone('Asia/Tehran')
    iran_time = datetime.now(iran_tz)
    return iran_time.strftime("%Y-%m-%dT%H:%M:%S")

def save_event_details_to_json(event_details):
    """
    ذخیره اطلاعات استخراج‌شده (چند رویداد به صورت JSON آرایه) در فایل‌های event_details.json و backup_event_details.json.
    """
    file_path = "event_details.json"
    backup_file_path = "backup_event_details.json"
    
    with file_lock:
        # خواندن داده‌های قبلی از فایل اصلی (در صورت وجود)
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                existing_data = json.load(file)
        except FileNotFoundError:
            existing_data = []
    
        try:
            # تلاش برای پارس کردن خروجی به عنوان یک آرایه JSON
            events = json.loads(event_details)
            if not isinstance(events, list):
                # در صورتیکه خروجی یک شیء JSON تکی باشد، آن را در یک لیست قرار می‌دهیم
                events = [events]
        except json.JSONDecodeError:
            # در صورت بروز خطا، تلاش می‌کنیم تا یک آرایه JSON با استفاده از regex استخراج کنیم
            match = re.search(r'(\[.*\])', event_details, re.DOTALL)
            if match:
                try:
                    events = json.loads(match.group(1))
                    if not isinstance(events, list):
                        events = [events]
                except json.JSONDecodeError:
                    print("خطا: امکان پارس کردن آرایه JSON استخراج شده وجود ندارد.")
                    return
            else:
                print("هیچ آرایه JSON معتبری در خروجی یافت نشد.")
                return
    
        # افزودن رویدادهای جدید به داده‌های قبلی (برای پشتیبان‌گیری کامل)
        existing_data.extend(events)
    
        # ذخیره پشتیبان
        with open(backup_file_path, "w", encoding="utf-8") as backup_file:
            json.dump(existing_data, backup_file, ensure_ascii=False, indent=4)
    
        # ذخیره تنها رویدادهای جدید در فایل اصلی
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(events, file, ensure_ascii=False, indent=4)

def extract_event_details(text):
    """
    دریافت متن ورودی و استخراج جزئیات رویدادها به کمک مدل زبانی.
    خروجی باید به صورت یک آرایه JSON از اشیاء رویداد باشد.
    """
    today_date = get_today_date()
    response = llm.predict(f"""
    Today is: '{today_date}'.
    Based on today, please extract ALL event details from the following text without omitting any events, even if the number of events is large. If there is only one event, output it as a JSON array with a single element.
    Ensure that the output is a complete JSON array containing all events.
    Make sure to extract the event’s date and time information exactly as specified in the text.
    If the text uses relative time expressions (such as "امروز", "فردا", "دیروز"), calculate the corresponding date using the reference date provided (today_date); note that the event date can be in the past.

    For a single (timed) event:
    - If a start time is provided but no end time is explicitly mentioned, try to infer a reasonable end time from the context (for example, if the event is "امشب ساعت ۹ ورزش", assume that the event lasts about one hour) and output the end time accordingly in ISO 8601 format ("YYYY-MM-DDTHH:MM:SS").  
    - If no time is provided at all, then based on the context and type of the event, automatically assign a reasonable default start and end time. For instance, if the event appears to be a meeting or an office event, you may assume a default start time of 09:00 and an end time one hour later; if the event seems more social (such as a party), you may assume a start time of 18:00 and a duration of around 3 hours. Use your best judgment to determine appropriate times.

    For an all-day event:
    - If the text indicates that the event lasts all day (using phrases like "تمام روز", "کل روز", or "all day"), output the event using the "date" property instead of "dateTime". For example, if the event is on 2025-02-11, then output:
        "start": {{ "date": "2025-02-11" }},
        "end": {{ "date": "2025-02-12" }}
    (Remember: For all-day events in Google Calendar, the end date is the day after the event date.)

    For each event, follow the format below:

    1. **Title of the event**: A short, clear name for the event.
    2. **Start Date and Time / Date**:  
    - For timed events: extract in ISO 8601 format (YYYY-MM-DDTHH:MM:SS) exactly as specified or as inferred from context.  
    - For all-day events: extract as "YYYY-MM-DD" in a field named "date".
    3. **End Date and Time / Date**:  
    - For timed events: extract in ISO 8601 format (YYYY-MM-DDTHH:MM:SS) exactly as specified or as inferred from context.  
    - For all-day events: extract as "YYYY-MM-DD" (which should be the day after the event date).
    4. **Description**: A brief explanation of the event.
    5. **Location**: If a location is mentioned, extract it; otherwise, use an empty string.
    6. **Recurrence Rule (RRULE)**: If the event repeats, extract the recurrence pattern as follows:
    - For weekly events on multiple days, use "BYDAY=XX,XX,XX" (ensure that Saturday is "SA" and Sunday is "SU").
    - For daily repetition, use "FREQ=DAILY;COUNT=N".
    - For monthly or yearly events, format the rule properly.
    - If no recurrence is found, return an empty list.
    7. **Event Color (colorId)**:
    Assign a color based on event type:
    - Work-related events → "1"
    - Health, medical, fitness → "2"
    - Personal projects, planning → "3"
    - Urgent deadlines, critical events → "4"
    - Reminders, small tasks → "5"
    - Important appointments, client meetings → "6"
    - Travel, vacations, leisure → "7"
    - Routine tasks, general admin work → "8"
    - Education, courses, training → "9"
    - Celebrations, special occasions → "10"
    - Strategic meetings, long-term planning → "11"
    - If no specific category is found, assign a reasonable default value.

    **📌 Format the output strictly as a JSON array (even if there is only one event). Each event object should have exactly the following structure:**

    For a timed event:
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

    For an all-day event:
    {{
        "summary": "Event Title",
        "start": {{ "date": "YYYY-MM-DD" }},
        "end": {{ "date": "YYYY-MM-DD" }},
        "location": "Event Location",
        "description": "Event Description",
        "recurrence": ["RRULE:FREQ=...;BYDAY=XX,XX;COUNT=N"] or [],
        "colorId": "X"
    }}

    Return the results as a JSON array containing ALL the events found.

    Text to analyze: '{text}'
    """)



    
    save_event_details_to_json(response)
    return response

def ask_chatbot(user_input):
    """
    تابع نهایی جهت پردازش ورودی کاربر؛ استخراج رویدادها و بازگرداندن جزئیات آن‌ها.
    """
    event_details = extract_event_details(user_input)
    return event_details
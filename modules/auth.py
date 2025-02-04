import os
import json
import requests
from flask import Flask, redirect, url_for, session, request
from oauthlib.oauth2 import WebApplicationClient
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی
load_dotenv()

# پیکربندی OAuth 2.0
client = WebApplicationClient(os.getenv("GOOGLE_CLIENT_ID"))
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

def login():
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri="http://127.0.0.1:5000/login/callback",  # مسیر بازگشت به درست تعریف شده است
        scope=["openid", "email", "profile", "https://www.googleapis.com/auth/calendar"]
    )
    return redirect(request_uri)

def callback():
    code = request.args.get("code")
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]
    
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(os.getenv("GOOGLE_CLIENT_ID"), os.getenv("GOOGLE_CLIENT_SECRET")),
    )
    client.parse_request_body_response(json.dumps(token_response.json()))
    
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    
    if userinfo_response.json().get("email_verified"):
        session["userinfo"] = userinfo_response.json()
        session["credentials"] = token_response.json()
        
        creds_data = session["credentials"].copy()
        creds_data['token'] = creds_data.pop('access_token', None)
        
        if not creds_data['token']:
            return "Token not found in credentials.", 400
        
        creds = Credentials(
            token=creds_data.get('token'),
            refresh_token=creds_data.get('refresh_token'),
            token_uri=creds_data.get('token_uri'),
            client_id=creds_data.get('client_id'),
            client_secret=creds_data.get('client_secret'),
            scopes=creds_data.get('scopes')
        )
        
        service = build("calendar", "v3", credentials=creds)
        calendar = service.calendars().get(calendarId='primary').execute()
        timezone = calendar.get('timeZone', 'UTC')
        session["timezone"] = timezone
        
        return redirect(url_for("chat"))  
    return "User email not available or not verified by Google.", 400

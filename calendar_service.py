import os
import json
from datetime import datetime, timedelta, timezone
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CLIENT_SECRETS_FILE = os.getenv("CLIENT_SECRETS_FILE", "client_secrets.json")


def get_auth_flow():
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri='http://localhost'
    )


def build_service(creds_json):
    creds_data = json.loads(creds_json)
    creds = Credentials.from_authorized_user_info(creds_data, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build('calendar', 'v3', credentials=creds), creds.to_json()


def get_upcoming_events(creds_json, minutes_ahead=30):
    try:
        service, updated_creds = build_service(creds_json)
        now = datetime.now(timezone.utc)
        time_max = now + timedelta(minutes=minutes_ahead)

        events_result = service.events().list(
            calendarId='primary',
            timeMin=now.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        return events_result.get('items', []), updated_creds
    except Exception as e:
        print(f"Ошибка при получении событий: {e}")
        return [], None


def check_past_events(creds_json):
    try:
        service, _ = build_service(creds_json)
        now = datetime.now(timezone.utc)
        time_min = now - timedelta(hours=1)

        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min.isoformat(),
            timeMax=now.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        return events_result.get('items', [])
    except Exception as e:
        print(f"Ошибка при получении прошедших событий: {e}")
        return []
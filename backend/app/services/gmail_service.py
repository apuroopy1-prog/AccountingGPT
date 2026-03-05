"""
Gmail OAuth2 service.
Handles authorization URL generation, token exchange, client creation,
and fetching invoice attachments from Gmail.
"""
import base64
import os
from datetime import datetime, timezone

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
MIME_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}


def get_auth_url(user_id: int) -> str:
    """Build and return the Google OAuth2 authorization URL."""
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        redirect_uri=os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/gmail/callback"),
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=str(user_id),
    )
    return auth_url


def exchange_code(code: str, user_id: int):
    """Exchange authorization code for access + refresh tokens. Returns token dict."""
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        redirect_uri=os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/gmail/callback"),
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    expiry = creds.expiry.replace(tzinfo=None) if creds.expiry else None
    return {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_expiry": expiry,
    }


def get_gmail_client(credentials, session=None):
    """
    Build an authenticated Gmail API service object.
    Auto-refreshes access token if expired and persists the new token to DB.
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    client_config = _client_config()["web"]
    creds = Credentials(
        token=credentials.access_token,
        refresh_token=credentials.refresh_token,
        token_uri=client_config["token_uri"],
        client_id=client_config["client_id"],
        client_secret=client_config["client_secret"],
        scopes=SCOPES,
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        if session is not None:
            credentials.access_token = creds.token
            expiry = creds.expiry.replace(tzinfo=None) if creds.expiry else None
            credentials.token_expiry = expiry
            session.commit()

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def fetch_invoice_attachments(service, since: datetime) -> list[tuple[str, bytes]]:
    """
    Fetch email attachments (PDF/image) received after `since`.
    Returns list of (filename, raw_bytes).
    """
    # Convert since to Unix timestamp for Gmail query
    since_ts = int(since.timestamp())
    query = f"after:{since_ts} has:attachment"

    results = service.users().messages().list(userId="me", q=query, maxResults=50).execute()
    messages = results.get("messages", [])

    attachments = []
    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()
        parts = _get_parts(msg.get("payload", {}))
        for part in parts:
            mime = part.get("mimeType", "")
            if mime not in MIME_TYPES:
                continue
            filename = part.get("filename") or f"attachment.{mime.split('/')[-1]}"
            body = part.get("body", {})
            attachment_id = body.get("attachmentId")
            if attachment_id:
                att = service.users().messages().attachments().get(
                    userId="me", messageId=msg_ref["id"], id=attachment_id
                ).execute()
                data = base64.urlsafe_b64decode(att["data"])
            elif body.get("data"):
                data = base64.urlsafe_b64decode(body["data"])
            else:
                continue
            attachments.append((filename, data))

    return attachments


def _get_parts(payload: dict) -> list[dict]:
    """Recursively extract all MIME parts from a message payload."""
    parts = []
    if payload.get("parts"):
        for part in payload["parts"]:
            parts.extend(_get_parts(part))
    else:
        parts.append(payload)
    return parts


def _client_config() -> dict:
    return {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/gmail/callback")
            ],
        }
    }

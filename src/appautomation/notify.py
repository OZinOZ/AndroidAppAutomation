"""Optional e-mail notifications through the Gmail API.

Setup (once):

1. Create an OAuth *Desktop* client in Google Cloud Console and enable the
   Gmail API.
2. Download the client secret as ``credentials.json`` (see
   ``credentials.example.json`` for the expected shape) -- **never commit it**.
3. Fill the ``email:`` section of ``config.yaml``.

The first notification opens a browser for consent and stores a refresh token
in ``token.json``.
"""

from __future__ import annotations

import base64
import logging
import os
from email.message import EmailMessage
from typing import Optional

from .config import EmailConfig

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]  # delete token.json if changed


def _load_credentials(cfg: EmailConfig):
    """Return valid OAuth credentials, refreshing or re-authorising if needed."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if os.path.exists(cfg.token_file):
        creds = Credentials.from_authorized_user_file(cfg.token_file, SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            logger.info("Refreshing Gmail credentials...")
            creds.refresh(Request())
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to refresh credentials (%s); re-authorising", exc)
            os.remove(cfg.token_file)
            creds = None
    else:
        creds = None

    if creds is None:
        flow = InstalledAppFlow.from_client_secrets_file(cfg.credentials_file, SCOPES)
        creds = flow.run_local_server(port=0)
        logger.info("New Gmail credentials generated")

    with open(cfg.token_file, "w", encoding="utf-8") as token:
        token.write(creds.to_json())
    return creds


def send_email(cfg: Optional[EmailConfig], subject: str, body: str) -> Optional[dict]:
    """Send ``body`` to ``cfg.recipient``. Does nothing when ``cfg`` is ``None``.

    Returns the Gmail API response, or ``None`` if nothing was sent.
    """
    if cfg is None:
        logger.info("E-mail not configured, skipping notification: %s", subject)
        return None

    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    try:
        service = build("gmail", "v1", credentials=_load_credentials(cfg), cache_discovery=False)
        message = EmailMessage()
        message.set_content(body)
        message["To"] = cfg.recipient
        message["From"] = cfg.sender
        message["Subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        logger.info("Message Id: %s", sent["id"])
        return sent
    except HttpError as error:
        logger.error("An error occurred while sending e-mail: %s", error)
        return None

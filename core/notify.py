"""Optional e-mail notifications for task completion and failures.

All settings come from environment variables so that nothing sensitive is
committed:

    NOTIFY_SMTP_HOST   SMTP server, e.g. smtp.gmail.com
    NOTIFY_SMTP_PORT   usually 465 (SSL) or 587 (TLS)
    NOTIFY_SMTP_USER   account name
    NOTIFY_SMTP_PASS   app password - use a dedicated app password, never your
                       real account password
    NOTIFY_MAIL_FROM   sender address (defaults to NOTIFY_SMTP_USER)
    NOTIFY_MAIL_TO     comma-separated recipient list

When the variables are absent the notifier degrades to logging only, so the
pipeline runs fine without e-mail.
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText


def send_message(title: str, body: str):
    host = os.environ.get('NOTIFY_SMTP_HOST')
    user = os.environ.get('NOTIFY_SMTP_USER')
    password = os.environ.get('NOTIFY_SMTP_PASS')
    receivers = [r.strip() for r in os.environ.get('NOTIFY_MAIL_TO', '').split(',') if r.strip()]

    if not (host and user and password and receivers):
        logging.warning('Notification skipped: NOTIFY_* environment variables are not set')
        return

    message = MIMEText(body)
    message['Subject'] = title
    message['From'] = os.environ.get('NOTIFY_MAIL_FROM', user)
    message['To'] = ', '.join(receivers)

    try:
        port = int(os.environ.get('NOTIFY_SMTP_PORT', '465'))
        if port == 465:
            with smtplib.SMTP_SSL(host, port) as server:
                server.login(user, password)
                server.send_message(message)
        else:
            with smtplib.SMTP(host, port) as server:
                server.starttls()
                server.login(user, password)
                server.send_message(message)
        logging.info('Notification sent: %s', title)
    except Exception as exc:  # never let notification failures kill the pipeline
        logging.error('Notification failed: %s', str(exc))

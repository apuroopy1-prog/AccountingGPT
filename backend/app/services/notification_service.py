import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def send_sms(recipient: str, message: str) -> dict:
    """
    Mock Twilio SMS.
    In production: replace with twilio.rest.Client calls.
    """
    log_msg = f"[MOCK SMS] To: {recipient} | Message: {message}"
    logger.info(log_msg)
    print(log_msg)

    return {
        "provider": "Twilio (mock)",
        "recipient": recipient,
        "message_preview": message[:50],
        "sent_at": datetime.utcnow().isoformat(),
    }


def send_email(recipient: str, message: str) -> dict:
    """
    Mock SendGrid email.
    In production: replace with sendgrid.SendGridAPIClient calls.
    """
    log_msg = f"[MOCK EMAIL] To: {recipient} | Message: {message}"
    logger.info(log_msg)
    print(log_msg)

    return {
        "provider": "SendGrid (mock)",
        "recipient": recipient,
        "message_preview": message[:50],
        "sent_at": datetime.utcnow().isoformat(),
    }

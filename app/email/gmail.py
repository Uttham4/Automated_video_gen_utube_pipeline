import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config.settings import settings

logger = logging.getLogger(__name__)

class GmailNotifier:
    def send_approval_email(self, title: str, episode_id: str, preview_url: str) -> bool:
        if not settings.GMAIL_SENDER_EMAIL or not settings.GMAIL_RECIPIENT_EMAIL:
            logger.warning(
                "Approval email not sent: configure GMAIL_SENDER_EMAIL and "
                "GMAIL_RECIPIENT_EMAIL to enable notifications"
            )
            return False
        if not settings.GMAIL_APP_PASSWORD:
            logger.warning(
                "Approval email not sent: configure GMAIL_APP_PASSWORD with a "
                "Google App Password"
            )
            return False

        subject = f"🎬 New Kids Video Ready for Approval: {title}"
        body = f"""
Hello Creator!

Your new animated video episode is rendered and awaiting your approval:

Title: {title}
Episode ID: {episode_id}

Preview & Approve Dashboard:
{preview_url}

Click APPROVE on the dashboard to publish directly to YouTube.
"""
        msg = MIMEMultipart()
        msg['From'] = settings.GMAIL_SENDER_EMAIL
        msg['To'] = settings.GMAIL_RECIPIENT_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(settings.GMAIL_SENDER_EMAIL, settings.GMAIL_APP_PASSWORD)
                server.send_message(msg)
        except Exception as e:
            logger.exception("Could not send approval email for %s: %s", episode_id, e)
            return False

        logger.info("Approval email sent for %s", episode_id)
        return True

gmail_notifier = GmailNotifier()

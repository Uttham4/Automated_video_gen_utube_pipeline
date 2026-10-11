import unittest
from unittest.mock import MagicMock, patch

from app.config.settings import settings
from app.email.gmail import GmailNotifier


class GmailNotifierTests(unittest.TestCase):
    def test_sends_authenticated_approval_email(self):
        smtp_server = MagicMock()
        with (
            patch.object(settings, "GMAIL_SENDER_EMAIL", "sender@example.com"),
            patch.object(settings, "GMAIL_RECIPIENT_EMAIL", "recipient@example.com"),
            patch.object(settings, "GMAIL_APP_PASSWORD", "app-password"),
            patch("app.email.gmail.smtplib.SMTP") as smtp,
        ):
            smtp.return_value.__enter__.return_value = smtp_server

            result = GmailNotifier().send_approval_email(
                "Test Story", "episode-123", "http://localhost:8000"
            )

        self.assertTrue(result)
        smtp.assert_called_once_with("smtp.gmail.com", 587)
        smtp_server.starttls.assert_called_once_with()
        smtp_server.login.assert_called_once_with("sender@example.com", "app-password")
        smtp_server.send_message.assert_called_once()
        message = smtp_server.send_message.call_args.args[0]
        self.assertEqual(message["To"], "recipient@example.com")
        self.assertIn("episode-123", message.get_payload()[0].get_payload())

    def test_does_not_attempt_smtp_without_app_password(self):
        with (
            patch.object(settings, "GMAIL_SENDER_EMAIL", "sender@example.com"),
            patch.object(settings, "GMAIL_RECIPIENT_EMAIL", "recipient@example.com"),
            patch.object(settings, "GMAIL_APP_PASSWORD", ""),
            patch("app.email.gmail.smtplib.SMTP") as smtp,
        ):
            result = GmailNotifier().send_approval_email(
                "Test Story", "episode-123", "http://localhost:8000"
            )

        self.assertFalse(result)
        smtp.assert_not_called()


if __name__ == "__main__":
    unittest.main()

import smtplib

import pytest

from app.core.config import Settings
from app.integrations.email.base import EmailDeliveryError, OutboundEmail
from app.integrations.email.smtp import SmtpEmailProvider


class RecordingSmtp:
    def __init__(self) -> None:
        self.ehlo_calls = 0
        self.starttls_calls = 0
        self.login_credentials: tuple[str, str] | None = None
        self.sent_messages = []

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def ehlo(self) -> None:
        self.ehlo_calls += 1

    def starttls(self, *, context) -> None:
        assert context is not None
        self.starttls_calls += 1

    def login(self, username: str, password: str) -> None:
        self.login_credentials = (username, password)

    def send_message(self, message) -> None:
        self.sent_messages.append(message)


def test_empty_sender_environment_value_means_smtp_is_unconfigured() -> None:
    assert Settings(_env_file=None, mail_from_email="").mail_from_email is None


def test_smtp_provider_uses_starttls_authentication_and_multipart_email(monkeypatch) -> None:
    smtp = RecordingSmtp()
    monkeypatch.setattr(smtplib, "SMTP", lambda *_args, **_kwargs: smtp)
    settings = Settings(
        _env_file=None,
        smtp_username="relay-user",
        smtp_password="relay-secret",
        mail_from_email="verified@example.com",
    )
    message = OutboundEmail(
        recipient="student@example.com",
        subject="Password reset",
        text_body="Text version",
        html_body="<p>HTML version</p>",
    )

    SmtpEmailProvider(settings).send(message)

    assert smtp.ehlo_calls == 2
    assert smtp.starttls_calls == 1
    assert smtp.login_credentials == ("relay-user", "relay-secret")
    assert len(smtp.sent_messages) == 1
    assert smtp.sent_messages[0]["To"] == "student@example.com"
    assert smtp.sent_messages[0].is_multipart()


def test_smtp_provider_fails_closed_without_verified_sender() -> None:
    settings = Settings(
        _env_file=None,
        smtp_username="relay-user",
        smtp_password="relay-secret",
        mail_from_email=None,
    )

    with pytest.raises(EmailDeliveryError):
        SmtpEmailProvider(settings).send(
            OutboundEmail(
                recipient="student@example.com",
                subject="Password reset",
                text_body="Text",
                html_body="<p>HTML</p>",
            )
        )


def test_smtp_provider_refuses_plaintext_credentials() -> None:
    settings = Settings(
        _env_file=None,
        smtp_username="relay-user",
        smtp_password="relay-secret",
        smtp_starttls=False,
        smtp_use_ssl=False,
        mail_from_email="verified@example.com",
    )

    with pytest.raises(EmailDeliveryError, match="encryption"):
        SmtpEmailProvider(settings).send(
            OutboundEmail(
                recipient="student@example.com",
                subject="Password reset",
                text_body="Text",
                html_body="<p>HTML</p>",
            )
        )

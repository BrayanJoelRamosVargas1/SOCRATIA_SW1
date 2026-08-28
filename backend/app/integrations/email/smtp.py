import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import Settings
from app.integrations.email.base import EmailDeliveryError, OutboundEmail


class SmtpEmailProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, message: OutboundEmail) -> None:
        password = self._validated_password()
        try:
            email = EmailMessage()
            email["From"] = formataddr(
                (self.settings.mail_from_name, str(self.settings.mail_from_email))
            )
            email["To"] = message.recipient
            email["Subject"] = message.subject
            email.set_content(message.text_body)
            email.add_alternative(message.html_body, subtype="html")

            context = ssl.create_default_context()
            if self.settings.smtp_use_ssl:
                with smtplib.SMTP_SSL(
                    self.settings.smtp_host,
                    self.settings.smtp_port,
                    timeout=self.settings.smtp_timeout_seconds,
                    context=context,
                ) as smtp:
                    self._authenticate_and_send(smtp, email, password)
            else:
                with smtplib.SMTP(
                    self.settings.smtp_host,
                    self.settings.smtp_port,
                    timeout=self.settings.smtp_timeout_seconds,
                ) as smtp:
                    smtp.ehlo()
                    if self.settings.smtp_starttls:
                        smtp.starttls(context=context)
                        smtp.ehlo()
                    self._authenticate_and_send(smtp, email, password)
        except (OSError, ValueError, smtplib.SMTPException) as exc:
            raise EmailDeliveryError(
                "The SMTP relay rejected or could not deliver the email."
            ) from exc

    def _validated_password(self) -> str:
        if self.settings.smtp_use_ssl and self.settings.smtp_starttls:
            raise EmailDeliveryError("SMTP_USE_SSL and SMTP_STARTTLS cannot both be enabled.")
        if not self.settings.smtp_use_ssl and not self.settings.smtp_starttls:
            raise EmailDeliveryError("SMTP transport encryption is required.")
        password = (
            self.settings.smtp_password.get_secret_value()
            if self.settings.smtp_password is not None
            else ""
        )
        if not all(
            (
                self.settings.smtp_host,
                self.settings.smtp_username,
                password,
                self.settings.mail_from_email,
            )
        ):
            raise EmailDeliveryError("SMTP credentials and a verified sender are required.")
        return password

    def _authenticate_and_send(
        self,
        smtp: smtplib.SMTP,
        email: EmailMessage,
        password: str,
    ) -> None:
        smtp.login(str(self.settings.smtp_username), password)
        smtp.send_message(email)
